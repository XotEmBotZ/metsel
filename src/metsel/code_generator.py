"""
GribCodeGenerator: Generates minimal, standalone Python data-loading scripts for GRIB files using xarray + cfgrib.
"""

from collections import defaultdict
from pathlib import Path


class GribCodeGenerator:
    """Generates clean, production-ready xarray/cfgrib data loading code based on user selections."""

    @staticmethod
    def generate(
        filepath: str,
        selected_msg_ids: set[str],
        raw_variables: dict[str, dict],
        grouped_variables: dict[str, dict] | None = None,
    ) -> str:
        """Generate standalone Python script that loads selected GRIB messages and levels into xarray Dataset."""
        if not selected_msg_ids:
            return GribCodeGenerator._generate_default_code(filepath)

        # Gather all selected messages
        selected_msgs = [
            raw_variables[msg_id]
            for msg_id in selected_msg_ids
            if msg_id in raw_variables
        ]

        if not selected_msgs:
            return GribCodeGenerator._generate_default_code(filepath)

        # Build map of total available levels in file per (shortName, typeOfLevel, stepType)
        file_levels_map: dict[tuple[str, str, str], set[int]] = defaultdict(set)
        for msg in raw_variables.values():
            key = (
                msg.get("shortName", ""),
                msg.get("typeOfLevel", "unknown"),
                msg.get("stepType", "instant"),
            )
            file_levels_map[key].add(msg.get("levelVal", 0))

        # Group selected messages by (shortName, typeOfLevel, stepType) to assess level subsets
        var_selected_map: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        for msg in selected_msgs:
            key = (
                msg.get("shortName", ""),
                msg.get("typeOfLevel", "unknown"),
                msg.get("stepType", "instant"),
            )
            var_selected_map[key].append(msg)

        # Group into slices by (typeOfLevel, stepType, level_filter)
        slice_groups: dict[tuple[str, str, frozenset[int] | None], list[dict]] = (
            defaultdict(list)
        )
        for (short_name, type_of_level, step_type), msgs in var_selected_map.items():
            selected_levels = {m.get("levelVal", 0) for m in msgs}
            total_levels = file_levels_map[(short_name, type_of_level, step_type)]

            # If only a subset of levels is selected, pass the level filter
            if len(selected_levels) < len(total_levels):
                level_key: frozenset[int] | None = frozenset(selected_levels)
            else:
                level_key = None  # All levels selected in file

            slice_groups[(type_of_level, step_type, level_key)].extend(msgs)

        # If only 1 slice group
        if len(slice_groups) == 1:
            (type_of_level, step_type, level_filter), msgs = next(
                iter(slice_groups.items())
            )
            return GribCodeGenerator._generate_single_slice_code(
                filepath, type_of_level, step_type, level_filter, msgs
            )

        # Multiple slice groups
        return GribCodeGenerator._generate_multi_slice_code(filepath, slice_groups)

    @staticmethod
    def _generate_default_code(filepath: str) -> str:
        lines = [
            '"""',
            f"Auto-generated GRIB data loading script via metsel for: {Path(filepath).name if filepath else 'data.grib2'}",
            "Engine: cfgrib with defensive read-only backend configuration.",
            '"""',
            "",
            "import xarray as xr",
            "",
            f"FILE_PATH = {filepath!r}",
            "",
            "# Defensive backend kwargs: indexpath='' prevents sidecar .idx file lock errors",
            "backend_kwargs = {",
            "    'indexpath': '',",
            "}",
            "",
            "ds = xr.open_dataset(",
            "    FILE_PATH,",
            "    engine='cfgrib',",
            "    backend_kwargs=backend_kwargs,",
            ")",
            "",
            "print(ds)",
        ]
        return "\n".join(lines)

    @staticmethod
    def _generate_single_slice_code(
        filepath: str,
        type_of_level: str,
        step_type: str,
        level_filter: frozenset[int] | None,
        msgs: list[dict],
    ) -> str:
        unique_vars = sorted({m["shortName"] for m in msgs})

        filter_keys = {
            "typeOfLevel": type_of_level,
        }
        if step_type and step_type != "unknown":
            filter_keys["stepType"] = step_type
        if unique_vars:
            filter_keys["shortName"] = (
                unique_vars if len(unique_vars) > 1 else unique_vars[0]
            )
        if level_filter is not None:
            sorted_levels = sorted(level_filter)
            filter_keys["level"] = (
                sorted_levels if len(sorted_levels) > 1 else sorted_levels[0]
            )

        lines = [
            '"""',
            f"Auto-generated GRIB data loading script via metsel for: {Path(filepath).name if filepath else 'data.grib2'}",
            "Target: xarray.Dataset using cfgrib engine with defensive backend configuration.",
            '"""',
            "",
            "import xarray as xr",
            "",
            f"FILE_PATH = {filepath!r}",
            "",
            "# Backend kwargs with message filters, selected levels, and read-only index safety",
            "backend_kwargs = {",
            "    'indexpath': '',",
            "    'filter_by_keys': {",
        ]
        for k, v in filter_keys.items():
            lines.append(f"        {k!r}: {v!r},")
        lines.extend(
            [
                "    },",
                "}",
                "",
                "ds = xr.open_dataset(",
                "    FILE_PATH,",
                "    engine='cfgrib',",
                "    backend_kwargs=backend_kwargs,",
                ")",
                "",
                "print(ds)",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _generate_multi_slice_code(
        filepath: str,
        slice_groups: dict[tuple[str, str, frozenset[int] | None], list[dict]],
    ) -> str:
        # Check if any variable name is shared across multiple level types
        shortname_levels: dict[str, set[str]] = defaultdict(set)
        for (type_of_level, _, _), msgs in slice_groups.items():
            for m in msgs:
                shortname_levels[m["shortName"]].add(type_of_level)

        has_var_collision = any(len(levels) > 1 for levels in shortname_levels.values())

        lines = [
            '"""',
            f"Auto-generated GRIB data loading script via metsel for: {Path(filepath).name if filepath else 'data.grib2'}",
            "Target: Multi-hypercube xarray.Dataset loaded via cfgrib engine.",
        ]
        if has_var_collision:
            lines.append(
                "Note: Uses type_of_level_in_header=True to prevent variable overwrite across levels."
            )
        lines.extend(
            [
                '"""',
                "",
                "import xarray as xr",
                "",
                f"FILE_PATH = {filepath!r}",
                "",
            ]
        )

        ds_names = []
        for idx, ((type_of_level, step_type, level_filter), msgs) in enumerate(
            slice_groups.items(), 1
        ):
            clean_level = type_of_level.replace(" ", "_").lower()
            var_name = f"ds_{clean_level}" if idx == 1 else f"ds_{clean_level}_{idx}"
            ds_names.append(var_name)
            unique_vars = sorted({m["shortName"] for m in msgs})

            filter_keys = {
                "typeOfLevel": type_of_level,
            }
            if step_type and step_type != "unknown":
                filter_keys["stepType"] = step_type
            if unique_vars:
                filter_keys["shortName"] = (
                    unique_vars if len(unique_vars) > 1 else unique_vars[0]
                )
            if level_filter is not None:
                sorted_levels = sorted(level_filter)
                filter_keys["level"] = (
                    sorted_levels if len(sorted_levels) > 1 else sorted_levels[0]
                )

            level_desc = f" (levels: {sorted(level_filter)})" if level_filter else ""
            lines.extend(
                [
                    f"# Slice {idx}: {type_of_level} ({step_type}){level_desc}",
                    f"{var_name} = xr.open_dataset(",
                    "    FILE_PATH,",
                    "    engine='cfgrib',",
                    "    backend_kwargs={",
                    "        'indexpath': '',",
                ]
            )
            if has_var_collision and any(
                len(shortname_levels[v]) > 1 for v in unique_vars
            ):
                lines.append(
                    "        'type_of_level_in_header': True,  # Disambiguate variable names across level types"
                )
            lines.append("        'filter_by_keys': {")
            for k, v in filter_keys.items():
                lines.append(f"            {k!r}: {v!r},")
            lines.extend(
                [
                    "        },",
                    "    },",
                    ")",
                    "",
                ]
            )

        lines.extend(
            [
                "# Merge loaded slices into a combined Dataset",
                f"ds = xr.merge([{', '.join(ds_names)}])",
                "",
                "print(ds)",
            ]
        )

        return "\n".join(lines)
