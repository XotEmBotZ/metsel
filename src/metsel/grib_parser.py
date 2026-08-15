import os
import struct
from pathlib import Path
from rapidfuzz import fuzz, process

# WMO GRIB2 Code Table 4.2 Parameter Lookups (Discipline 0)
GRIB2_PARAM_TABLE = {
    (0, 0): ("tmp", "Temperature", "K"),
    (0, 1): ("vptmp", "Virtual Potential Temperature", "K"),
    (0, 2): ("pot", "Potential Temperature", "K"),
    (0, 3): ("dpt", "Dew Point Temperature", "K"),
    (1, 0): ("spfh", "Specific Humidity", "kg kg**-1"),
    (1, 1): ("rh", "Relative Humidity", "%"),
    (1, 2): ("pwat", "Precipitable Water", "kg m**-2"),
    (2, 2): ("ugrd", "U-component of Wind", "m s**-1"),
    (2, 3): ("vgrd", "V-component of Wind", "m s**-1"),
    (2, 8): ("vort", "Vorticity", "s**-1"),
    (2, 9): ("dzdt", "Vertical Velocity", "Pa s**-1"),
    (2, 225): ("cape", "Convective Available Potential Energy", "J kg**-1"),
    (2, 226): ("cin", "Convective Inhibition", "J kg**-1"),
    (3, 0): ("pres", "Pressure", "Pa"),
    (3, 1): ("prmsl", "Pressure Reduced to MSL", "Pa"),
    (3, 5): ("gh", "Geopotential Height", "gpm"),
    (3, 6): ("alt", "Altimeter Setting", "Pa"),
}

# WMO GRIB2 Code Table 4.5 Surface/Level Type Lookups
GRIB2_LEVEL_TABLE = {
    1: ("surface", "Ground or Water Surface"),
    100: ("isobaricInhPa", "Isobaric Surface"),
    101: ("meanSea", "Mean Sea Level"),
    102: ("altitudeAboveMSL", "Specific Altitude Above MSL"),
    103: ("heightAboveGround", "Specified Height Level Above Ground"),
    104: ("sigma", "Sigma Level"),
    105: ("hybrid", "Hybrid Level"),
    106: ("depthBelowLand", "Depth Below Land Surface"),
}

CENTER_LOOKUP = {
    7: "US National Weather Service - NCEP",
    98: "ECMWF",
    34: "Japanese Meteorological Agency",
    54: "Canadian Meteorological Center",
}


class GribParser:
    """Fast pure-Python GRIB2 reader & metadata extractor."""

    @staticmethod
    def inspect_file(filepath: str) -> dict:
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

                edition = header[7]
                file_meta["edition"] = f"GRIB Edition {edition}"

                # Parse GRIB2 Sections
                idx = 0
                cat, num, level_type, level_val = 0, 0, 0, 0
                scan_mode = "+i -j"
                grid_type = "regular_ll"
                points = 0
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
                        discipline = s_data[9] if len(s_data) > 9 else 0
                        cat = s_data[9]
                        num = s_data[10]
                        level_type = s_data[22]
                        raw_level_val = int.from_bytes(s_data[24:28], "big")
                        level_val = raw_level_val // 100 if level_type == 100 else raw_level_val

                    idx += sec_len

                # Lookup Parameter metadata
                param_tuple = GRIB2_PARAM_TABLE.get((cat, num), (f"var_{cat}_{num}", f"Parameter ({cat}, {num})", "unknown"))
                short_name, full_name, units = param_tuple

                level_info = GRIB2_LEVEL_TABLE.get(level_type, (f"level_{level_type}", f"Level Type {level_type}"))
                type_of_level, level_desc = level_info

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
                    "points": points_str if 'points_str' in locals() else f"{points:,}",
                    "latRange": lat_range,
                    "lonRange": lon_range,
                    "scanningMode": scan_mode,
                    "earthShape": "6371229.0 m sphere",
                    "dataPacking": "JPEG 2000 (Template 5.40)",
                    "msgSize": f"{total_len:,} bytes",
                    "precision": "16-bit float",
                    "bitmap": "None (Full Grid)",
                    "discipline": f"{header[6]} (Meteorological)",
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

    import subprocess

    input_path = Path(user_input).expanduser()

    # Determine base directory to search
    if input_path.is_dir():
        base_dir = input_path
        filename_query = ""
    elif input_path.parent.exists():
        base_dir = input_path.parent
        filename_query = input_path.name
    else:
        base_dir = Path(".")
        filename_query = user_input

    # Fast system find command (max 2 levels deep, ignoring hidden files)
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
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.0)
        if res.returncode == 0:
            candidate_files = [line for line in res.stdout.splitlines() if line]
    except Exception:
        pass

    if not candidate_files:
        return []

    if not filename_query:
        return candidate_files[:10]

    matches = process.extract(filename_query, candidate_files, scorer=fuzz.partial_ratio, limit=10)
    return [m[0] for m in matches if m[1] > 40]


def fuzzy_filter_variables(query: str, variables: dict[str, dict]) -> dict[str, dict]:
    """Fuzzy filter variable messages across all parameters (Grp 1 & Grp 2 metadata)."""
    if not query.strip():
        return variables

    query_lower = query.lower()
    filtered = {}

    for msg_id, var in variables.items():
        # Combine all Grp 1 & 2 details into a single search target string
        search_blob = f"{msg_id} {var['shortName']} {var['name']} {var['level']} {var['typeOfLevel']} {var['step']} {var['units']} {var['category']}".lower()

        # Score matching using RapidFuzz partial ratio
        score = fuzz.partial_ratio(query_lower, search_blob)
        if score > 60 or query_lower in search_blob:
            filtered[msg_id] = var

    return filtered
