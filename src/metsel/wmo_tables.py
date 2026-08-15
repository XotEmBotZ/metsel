"""WMO Code Tables for GRIB2 Metadata Lookup."""

# WMO GRIB2 Code Table 4.2 Parameter Lookups (Discipline 0: Meteorological Products)
# Key: (category, parameter_number) -> (short_name, full_name, units)
GRIB2_PARAM_TABLE = {
    # Category 0: Temperature
    (0, 0): ("tmp", "Temperature", "K"),
    (0, 1): ("vptmp", "Virtual Potential Temperature", "K"),
    (0, 2): ("pot", "Potential Temperature", "K"),
    (0, 3): ("dpt", "Dew Point Temperature", "K"),
    (0, 4): ("dewpt", "Dew Point Depression", "K"),
    (0, 5): ("lapr", "Lapse Rate", "K m**-1"),
    (0, 6): ("mapt", "Maximum Temperature", "K"),
    (0, 7): ("mipt", "Minimum Temperature", "K"),
    (0, 8): ("dalr", "Dry Adiabatic Lapse Rate", "K m**-1"),
    (0, 10): ("latp", "Latent Heat Net Flux", "W m**-2"),
    (0, 11): ("senp", "Sensible Heat Net Flux", "W m**-2"),

    # Category 1: Moisture
    (1, 0): ("spfh", "Specific Humidity", "kg kg**-1"),
    (1, 1): ("rh", "Relative Humidity", "%"),
    (1, 2): ("pwat", "Precipitable Water", "kg m**-2"),
    (1, 3): ("evap", "Evaporation", "kg m**-2"),
    (1, 7): ("prate", "Precipitation Rate", "kg m**-2 s**-1"),
    (1, 8): ("apcp", "Total Precipitation", "kg m**-2"),
    (1, 9): ("ncpcp", "Large-Scale Precipitation", "kg m**-2"),
    (1, 10): ("acpcp", "Convective Precipitation", "kg m**-2"),
    (1, 11): ("snow", "Snow Depth", "m"),
    (1, 13): ("weasd", "Water Equivalent of Accumulated Snow Depth", "kg m**-2"),
    (1, 19): ("cwat", "Cloud Water", "kg m**-2"),

    # Category 2: Momentum
    (2, 0): ("wind", "Wind Speed", "m s**-1"),
    (2, 1): ("wdir", "Wind Direction", "deg"),
    (2, 2): ("ugrd", "U-component of Wind", "m s**-1"),
    (2, 3): ("vgrd", "V-component of Wind", "m s**-1"),
    (2, 8): ("vort", "Vorticity", "s**-1"),
    (2, 9): ("dzdt", "Vertical Velocity", "Pa s**-1"),
    (2, 10): ("wmi", "Geometric Vertical Velocity", "m s**-1"),
    (2, 11): ("diverg", "Divergence", "s**-1"),
    (2, 14): ("gust", "Wind Gust", "m s**-1"),
    (2, 225): ("cape", "Convective Available Potential Energy", "J kg**-1"),
    (2, 226): ("cin", "Convective Inhibition", "J kg**-1"),

    # Category 3: Mass
    (3, 0): ("pres", "Pressure", "Pa"),
    (3, 1): ("prmsl", "Pressure Reduced to MSL", "Pa"),
    (3, 2): ("ptend", "Pressure Tendency", "Pa s**-1"),
    (3, 3): ("icaht", "ICAO Standard Atmosphere Reference Height", "m"),
    (3, 4): ("gp", "Geopotential", "m**2 s**-2"),
    (3, 5): ("gh", "Geopotential Height", "gpm"),
    (3, 6): ("alt", "Altimeter Setting", "Pa"),
    (3, 9): ("hgt", "Geometric Height", "m"),

    # Category 4: Short-wave Radiation
    (4, 0): ("nswrs", "Net Short-Wave Radiation Flux (Surface)", "W m**-2"),
    (4, 1): ("nswrt", "Net Short-Wave Radiation Flux (Top of Atmosphere)", "W m**-2"),
    (4, 2): ("dswrf", "Downward Short-Wave Radiation Flux", "W m**-2"),
    (4, 3): ("uswrf", "Upward Short-Wave Radiation Flux", "W m**-2"),

    # Category 5: Long-wave Radiation
    (5, 0): ("nlwrs", "Net Long-Wave Radiation Flux (Surface)", "W m**-2"),
    (5, 1): ("nlwrt", "Net Long-Wave Radiation Flux (Top of Atmosphere)", "W m**-2"),
    (5, 2): ("dlwrf", "Downward Long-Wave Radiation Flux", "W m**-2"),
    (5, 3): ("ulwrf", "Upward Long-Wave Radiation Flux", "W m**-2"),

    # Category 6: Cloud
    (6, 0): ("cice", "Cloud Ice", "kg m**-2"),
    (6, 1): ("tcc", "Total Cloud Cover", "%"),
    (6, 2): ("lcc", "Low Cloud Cover", "%"),
    (6, 3): ("mcc", "Medium Cloud Cover", "%"),
    (6, 4): ("hcc", "High Cloud Cover", "%"),

    # Category 19: Physical Atmospheric Properties
    (19, 0): ("vis", "Visibility", "m"),
    (19, 1): ("albedo", "Albedo", "%"),
}

# WMO GRIB2 Code Table 4.5 Surface/Level Type Lookups
GRIB2_LEVEL_TABLE = {
    1: ("surface", "Ground or Water Surface"),
    2: ("cloudBase", "Cloud Base Level"),
    3: ("cloudTop", "Cloud Top Level"),
    4: ("isothermZero", "0 Degree C Isotherm Level"),
    6: ("maxWind", "Maximum Wind Level"),
    7: ("tropopause", "Tropopause"),
    8: ("topOfAtmosphere", "Top of Atmosphere"),
    100: ("isobaricInhPa", "Isobaric Surface"),
    101: ("meanSea", "Mean Sea Level"),
    102: ("altitudeAboveMSL", "Specific Altitude Above MSL"),
    103: ("heightAboveGround", "Specified Height Level Above Ground"),
    104: ("sigma", "Sigma Level"),
    105: ("hybrid", "Hybrid Level"),
    106: ("depthBelowLand", "Depth Below Land Surface"),
    107: ("isentropic", "Isentropic (Potential Temp) Level"),
}

# WMO Code Table 0.0 Discipline Lookups
DISCIPLINE_LOOKUP = {
    0: "Meteorological Products",
    1: "Hydrological Products",
    2: "Land Surface Products",
    3: "Space Products",
    10: "Oceanographic Products",
}

# Common Originating Center Lookups (Common Code Table C-1)
CENTER_LOOKUP = {
    7: "US National Weather Service - NCEP",
    8: "US National Weather Service - NWSTG",
    9: "US National Weather Service - Other",
    34: "Japanese Meteorological Agency - Tokyo",
    54: "Canadian Meteorological Center",
    57: "U.S. Air Force Weather Agency",
    58: "US Navy Fleet Numerical Meteorology and Oceanography Center",
    59: "NOAA Forecast Systems Laboratory",
    74: "UK Met Office - Exeter",
    85: "French Weather Service - Toulouse",
    98: "European Centre for Medium-Range Weather Forecasts (ECMWF)",
    215: "NCAR - National Center for Atmospheric Research",
}
