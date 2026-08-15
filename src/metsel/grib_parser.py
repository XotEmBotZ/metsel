import subprocess
from pathlib import Path

from rapidfuzz import fuzz, process

from metsel.wmo_tables import (
    CENTER_LOOKUP,
    DISCIPLINE_LOOKUP,
    GRIB2_LEVEL_TABLE,
    GRIB2_PARAM_TABLE,
)

# Attempt eccodes import for dynamic backend lookup if available
HAS_ECCODES = False
try:
    import eccodes  # type: ignore[import-untyped]
    HAS_ECCODES = True
except Exception:  # noqa: BLE001
    eccodes = None
    HAS_ECCODES = False


class GribParser:
    """Fast pure-Python GRIB2 reader & metadata extractor with dynamic eccodes fallback."""

    @staticmethod
    def _inspect_eccodes(filepath: str) -> dict | None:
        """Inspect file using eccodes dynamic tables if available."""
        if not HAS_ECCODES or eccodes is None:
            return None

        try:
            path = Path(filepath)
            size_bytes = path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            messages = []
            file_meta = {
                "path": str(path),
                "size": f"{size_mb:.1f} MB ({size_bytes:,} bytes)",
                "total_msgs": 0,
                "edition": "GRIB2",
                "center": "Unknown",
                "ref_time": "N/A",
                "tables_version": "N/A",
            }

            with open(path, "rb") as f:
                msg_count = 0
                while True:
                    gid = eccodes.codes_grib_new_from_file(f)
                    if gid is None:
                        break
                    msg_count += 1

                    try:
                        short_name = eccodes.codes_get_string(gid, "shortName")
                        name = eccodes.codes_get_string(gid, "name")
                        units = eccodes.codes_get_string(gid, "units")
                        param_id = eccodes.codes_get_long(gid, "paramId")
                        type_of_level = eccodes.codes_get_string(gid, "typeOfLevel")
                        level = eccodes.codes_get_long(gid, "level")
                        discipline = eccodes.codes_get_string(gid, "discipline")
                        center = eccodes.codes_get_string(gid, "centre")
                        date_str = str(eccodes.codes_get_long(gid, "date"))
                        time_val = eccodes.codes_get_long(gid, "time")
                        grid_type = eccodes.codes_get_string(gid, "gridType")
                        num_points = eccodes.codes_get_long(gid, "numberOfDataPoints")

                        if msg_count == 1:
                            file_meta["center"] = center
                            file_meta["ref_time"] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_val:04d} UTC"

                        level_str = f"{level}"
                        msg_data = {
                            "msg_id": str(msg_count),
                            "shortName": short_name,
                            "name": name,
                            "units": units,
                            "paramId": param_id,
                            "cfVarName": short_name,
                            "level": level_str,
                            "typeOfLevel": type_of_level,
                            "levelVal": level,
                            "step": "0h (Instant)",
                            "stepType": "instant",
                            "refTime": file_meta["ref_time"],
                            "gridType": grid_type,
                            "gridTemplate": "Dynamic Template",
                            "points": f"{num_points:,}",
                            "latRange": "N/A",
                            "lonRange": "N/A",
                            "scanningMode": "Dynamic",
                            "earthShape": "Earth Sphere",
                            "dataPacking": "ECMWF Dynamic",
                            "msgSize": "N/A",
                            "precision": "Float",
                            "bitmap": "None",
                            "discipline": discipline,
                            "category": name,
                        }
                        messages.append(msg_data)
                    finally:
                        eccodes.codes_release(gid)

            if msg_count > 0:
                file_meta["total_msgs"] = msg_count
                return {"file_meta": file_meta, "variables": {m["msg_id"]: m for m in messages}}
        except Exception:  # noqa: BLE001
            return None

        return None

    @staticmethod
    def inspect_file(filepath: str) -> dict:
        # Try dynamic eccodes extraction first if supported
        eccodes_res = GribParser._inspect_eccodes(filepath)
        if eccodes_res is not None:
            return eccodes_res

        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")

        size_bytes = path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        messages = []
        file_meta = {
            "path": str(path),
            "size": f"{size_mb:.1f} MB ({size_bytes:,} bytes)",
            "total_msgs": 0,
            "edition": "GRIB2",
            "center": "Unknown",
            "ref_time": "N/A",
            "tables_version": "N/A",
        }

        with open(path, "rb") as f:
            msg_count = 0
            while True:
                header = f.read(16)
                if not header or len(header) < 16 or header[:4] != b"GRIB":
                    break

                total_len = int.from_bytes(header[8:16], "big")
                rest = f.read(total_len - 16)
                msg_count += 1

                discipline_code = header[6]
                discipline_name = DISCIPLINE_LOOKUP.get(discipline_code, f"Discipline {discipline_code}")
                edition = header[7]
                file_meta["edition"] = f"GRIB Edition {edition}"

                # Parse GRIB2 Sections
                idx = 0
                cat, num, level_type, level_val = 0, 0, 0, 0
                scan_mode = "+i -j"
                grid_type = "regular_ll"
                points = 0
                points_str = "0"
                lat_range = "N/A"
                lon_range = "N/A"

                while idx < len(rest) - 4:
                    if rest[idx : idx + 4] == b"7777":
                        break

                    sec_len = int.from_bytes(rest[idx : idx + 4], "big")
                    if sec_len < 5:
                        break

                    sec_num = rest[idx + 4]
                    s_data = rest[idx : idx + sec_len]

                    # Section 1: Identification
                    if sec_num == 1 and len(s_data) >= 21:
                        center_id = int.from_bytes(s_data[5:7], "big")
                        file_meta["center"] = CENTER_LOOKUP.get(center_id, f"Center ID {center_id}")
                        file_meta["tables_version"] = f"Version {s_data[9]}"
                        yr = int.from_bytes(s_data[12:14], "big")
                        mo, dy, hr, mn, sc = s_data[14], s_data[15], s_data[16], s_data[17], s_data[18]
                        file_meta["ref_time"] = f"{yr:04d}-{mo:02d}-{dy:02d} {hr:02d}:{mn:02d}:{sc:02d} UTC"

                    # Section 3: Grid Definition
                    elif sec_num == 3 and len(s_data) >= 14:
                        points = int.from_bytes(s_data[6:10], "big")
                        if len(s_data) >= 70:
                            ni = int.from_bytes(s_data[30:34], "big")
                            nj = int.from_bytes(s_data[34:38], "big")
                            points_str = f"{points:,} ({ni} x {nj})"
                            lat1 = int.from_bytes(s_data[46:50], "big", signed=True) / 1e6
                            lon1 = int.from_bytes(s_data[50:54], "big", signed=True) / 1e6
                            lat2 = int.from_bytes(s_data[55:59], "big", signed=True) / 1e6
                            lon2 = int.from_bytes(s_data[59:63], "big", signed=True) / 1e6
                            lat_range = f"{lat1:.2f}°N to {lat2:.2f}°S"
                            lon_range = f"{lon1:.2f}°E to {lon2:.2f}°E"
                        else:
                            points_str = f"{points:,}"

                    # Section 4: Product Definition
                    elif sec_num == 4 and len(s_data) >= 30:
                        cat = s_data[9]
                        num = s_data[10]
                        level_type = s_data[22]
                        raw_level_val = int.from_bytes(s_data[24:28], "big")
                        level_val = raw_level_val // 100 if level_type == 100 else raw_level_val

                    idx += sec_len

                # Lookup Parameter metadata from wmo_tables
                param_tuple = GRIB2_PARAM_TABLE.get((cat, num), (f"var_{cat}_{num}", f"Parameter ({cat}, {num})", "unknown"))
                short_name, full_name, units = param_tuple

                level_info = GRIB2_LEVEL_TABLE.get(level_type, (f"level_{level_type}", f"Level Type {level_type}"))
                type_of_level, _level_desc = level_info

                level_str = f"{level_val} hPa" if level_type == 100 else (f"{level_val} m" if level_type == 103 else f"{level_val}")

                msg_data = {
                    "msg_id": str(msg_count),
                    "shortName": short_name,
                    "name": full_name,
                    "units": units,
                    "paramId": cat * 1000 + num,
                    "cfVarName": short_name,
                    "level": level_str,
                    "typeOfLevel": type_of_level,
                    "levelVal": level_val,
                    "step": "0h (Instant)",
                    "stepType": "instant",
                    "refTime": file_meta["ref_time"],
                    "gridType": grid_type,
                    "gridTemplate": "Template 3.0",
                    "points": points_str,
                    "latRange": lat_range,
                    "lonRange": lon_range,
                    "scanningMode": scan_mode,
                    "earthShape": "6371229.0 m sphere",
                    "dataPacking": "JPEG 2000 (Template 5.40)",
                    "msgSize": f"{total_len:,} bytes",
                    "precision": "16-bit float",
                    "bitmap": "None (Full Grid)",
                    "discipline": f"{discipline_code} ({discipline_name})",
                    "category": f"{cat} ({full_name})",
                }
                messages.append(msg_data)

            file_meta["total_msgs"] = msg_count
            return {"file_meta": file_meta, "variables": {m["msg_id"]: m for m in messages}}


def fuzzy_search_files(user_input: str) -> list[str]:
    """Find matching files using system `find` command (max 2 levels deep, instant performance)."""
    user_input = user_input.strip()
    if not user_input:
        return []

    input_path = Path(user_input).expanduser()

    if input_path.is_dir():
        base_dir = input_path
        filename_query = ""
    elif input_path.parent.exists():
        base_dir = input_path.parent
        filename_query = input_path.name
    else:
        base_dir = Path(".")
        filename_query = user_input

    candidate_files = []
    try:
        cmd = [
            "find",
            str(base_dir),
            "-maxdepth",
            "3",
            "-type",
            "f",
            "!",
            "-path",
            "*/.*",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.0, check=False)
        if res.returncode == 0:
            candidate_files = [line for line in res.stdout.splitlines() if line]
    except Exception:  # noqa: BLE001, S110
        pass

    if not candidate_files:
        return []

    if not filename_query:
        return candidate_files[:10]

    matches = process.extract(filename_query, candidate_files, scorer=fuzz.partial_ratio, limit=10)
    return [m[0] for m in matches if m[1] > 40]


def compress_ranges(numbers: list[int]) -> str:
    """Compress a list of integers into a human readable range string like '1-3, 5, 7, 10-1000'."""
    if not numbers:
        return ""
    sorted_nums = sorted(set(numbers))
    ranges = []
    start = sorted_nums[0]
    end = sorted_nums[0]

    for n in sorted_nums[1:]:
        if n == end + 1:
            end = n
        else:
            ranges.append(f"{start}-{end}" if start != end else f"{start}")
            start = end = n
    ranges.append(f"{start}-{end}" if start != end else f"{start}")
    return ", ".join(ranges)


def group_variables(raw_variables: dict[str, dict]) -> dict[str, dict]:
    """Group GRIB messages by (shortName, typeOfLevel, name, units, step)."""
    groups_map: dict[tuple, list[dict]] = {}

    for v in raw_variables.values():
        key = (v["shortName"], v["typeOfLevel"], v["name"], v["units"], v["step"])
        if key not in groups_map:
            groups_map[key] = []
        groups_map[key].append(v)

    grouped_variables: dict[str, dict] = {}
    for idx, (key, msg_list) in enumerate(groups_map.items(), 1):
        group_id = f"grp_{idx}"
        short_name, type_of_level, name, units, step = key

        levels = [m["levelVal"] for m in msg_list]
        compressed_range = compress_ranges(levels)
        first_msg = msg_list[0]

        unit_str = "hPa" if type_of_level == "isobaricInhPa" else ("m" if type_of_level == "heightAboveGround" else "")
        level_display = f"[{compressed_range}] {unit_str}".strip() if compressed_range else first_msg["level"]

        grouped_variables[group_id] = {
            "group_id": group_id,
            "shortName": short_name,
            "name": name,
            "units": units,
            "typeOfLevel": type_of_level,
            "step": step,
            "stepType": first_msg["stepType"],
            "levelDisplay": level_display,
            "compressedRange": compressed_range,
            "msg_list": msg_list,
            "msg_ids": [m["msg_id"] for m in msg_list],
            "paramId": first_msg["paramId"],
            "cfVarName": first_msg["cfVarName"],
            "refTime": first_msg["refTime"],
            "gridType": first_msg["gridType"],
            "gridTemplate": first_msg["gridTemplate"],
            "points": first_msg["points"],
            "latRange": first_msg["latRange"],
            "lonRange": first_msg["lonRange"],
            "scanningMode": first_msg["scanningMode"],
            "earthShape": first_msg["earthShape"],
            "dataPacking": first_msg["dataPacking"],
            "msgSize": first_msg["msgSize"],
            "precision": first_msg["precision"],
            "bitmap": first_msg["bitmap"],
            "discipline": first_msg["discipline"],
            "category": first_msg["category"],
        }

    return grouped_variables


def fuzzy_filter_variables(query: str, grouped_variables: dict[str, dict]) -> dict[str, dict]:
    """Fuzzy filter grouped variables across shortName, description, levelType, etc."""
    if not query.strip():
        return grouped_variables

    query_lower = query.lower()
    filtered = {}

    for group_id, grp in grouped_variables.items():
        search_blob = f"{grp['group_id']} {grp['shortName']} {grp['name']} {grp['levelDisplay']} {grp['typeOfLevel']} {grp['step']} {grp['units']} {grp['category']}".lower()

        score = fuzz.partial_ratio(query_lower, search_blob)
        if score > 60 or query_lower in search_blob:
            filtered[group_id] = grp

    return filtered
