"""
The collections module house DataCollection classes, which define objects with data and metadata for a variable at a
given location and over a given time period.
"""

import numpy as np
from abc import ABC, abstractmethod

from .types import *
from . import maximal_limits
from .formatting import time_to_suffix
from .info_classes import Dataset, Variable
from .grid_data_input import get_interpreted_grid, re_shape_grids, get_years, get_months


class DataCollection(ABC):
    """
    The parent class for all collections of data at a given location and over a given time period. Includes
    only metadata, and abstract method for accessing data in time.
    """
    def __init__(self, dataset: Dataset, variable: Variable, time: TIME, time_stamps: TIME_STAMPS, title_prefix: str,
                 title_suffix: str):
        """
        Constructor method.
        Args:
            dataset: The dataset.
            variable: The variable.
            time: The time period over which the data spans.
            time_stamps: List of times, one for each time slice of data, which describe a time for each slice.
            title_prefix: Prefix for describing each time slice of data.
            title_suffix: Suffix for describing each time slice of data.
        """
        self.dataset = dataset
        self.variable = variable
        self.time = time
        self.time_stamps = time_stamps
        self.title_prefix = title_prefix
        self.title_suffix = title_suffix

    def __str__(self):
        return f'{self.title_prefix}{time_to_suffix(self.time)}{self.title_suffix}'

    def get_time_title(self, time_index) -> str:
        """
        The title of the DataCollection at a certain time.
        Args:
            time_index: The time index.

        Returns:
            The title.
        """
        return f'{self.title_prefix}{time_to_suffix(self.time_stamps[time_index])}{self.title_suffix}'

    def get_time_length(self) -> int:
        """
        The length of the DataCollection's data in time.

        Returns:
            The time length.
        """
        return len(self.time_stamps)

    @abstractmethod
    def get_time_data(self, time_index: int) -> DATA:
        ...

    @abstractmethod
    def get_limits(self) -> LIMITS:
        ...

    @abstractmethod
    def get_dimension(self) -> int:
        ...


class VectorCollection(DataCollection):
    """
    Class storing all information for Earth vector (or scalar) data, including its dataset, variable, time,
    etc. This might, for example, store wind speed over time for a square region on the Earth.
    """
    def __init__(self, dataset: Dataset, variable: Variable, time: TIME, time_stamps: TIME_STAMPS, title_prefix: str,
                 title_suffix: str, data_in_time: VECTOR_GRID_IN_TIME, latitude: COORDINATES, longitude: COORDINATES):
        # Validate parameters
        if len(data_in_time) != len(time_stamps):
            raise ValueError('The length of the data in time must be equal to the length of the time stamps.')

        super().__init__(dataset, variable, time, time_stamps, title_prefix, title_suffix)
        self.data_in_time = data_in_time
        self.latitude = latitude
        self.longitude = longitude

    def get_time_data(self, time_index: int) -> VECTOR_GRID:
        return self.data_in_time[time_index]

    def get_limits(self) -> LIMITS:
        """
        The spatial limits of the data. These are the maximal limits over time.

        Returns:
            The limits.
        """
        return np.min(self.latitude), np.max(self.latitude), np.min(self.longitude), np.max(self.longitude)

    def get_dimension(self) -> int:
        return self.variable.dimension


class VirtualVectorCollection(DataCollection):
    """
    Class storing all information for Earth vector (or scalar) data, including its dataset, variable, time,
    etc. This might, for example, store wind speed over time for a square region on the Earth. The data itself is not
    permanently stored, but accessed as requested.
    """
    def __init__(self, dataset: Dataset, variable: Variable, time: TIME, time_stamps: TIME_STAMPS, title_prefix: str,
                 title_suffix: str, latitude: COORDINATES, longitude: COORDINATES, idx_limits: IDX_LIMITS):
        super().__init__(dataset, variable, time, time_stamps, title_prefix, title_suffix)
        self.latitude = latitude
        self.longitude = longitude
        self.idx_limits = idx_limits

    def get_time_data(self, time_index: int) -> VECTOR_GRID:
        # Identify time
        time = self.time_stamps[time_index]

        # Return 0-th index of re-shaped and interpreted data, since this data is in time
        return re_shape_grids(get_interpreted_grid(self.dataset, self.variable, time, self.idx_limits))[0]

    def get_all_data(self):
        year, month, day, hour = self.time
        if (month is not None) and year is None:
            years = [x for x in get_years(self.dataset, None) if month in get_months(self.dataset, x, self.variable)]
            for year in years:
                yield re_shape_grids(get_interpreted_grid(self.dataset, self.variable, (year, month, None, None),
                                                          self.idx_limits))
        elif year is None:
            for year in get_years(self.dataset, self.variable):
                for month in get_months(self.dataset, year, self.variable):
                    yield re_shape_grids(get_interpreted_grid(self.dataset, self.variable, (year, month, None, None),
                                                              self.idx_limits))

        elif month is None:
            for month in get_months(self.dataset, year, self.variable):
                yield re_shape_grids(get_interpreted_grid(self.dataset, self.variable, (year, month, None, None),
                                                          self.idx_limits))

        else:
            yield re_shape_grids(get_interpreted_grid(self.dataset, self.variable, self.time, self.idx_limits))

    def get_limits(self) -> LIMITS:
        """
        The spatial limits of the data. These are the maximal limits over time.

        Returns:
            The limits.
        """
        return np.min(self.latitude), np.max(self.latitude), np.min(self.longitude), np.max(self.longitude)

    def get_dimension(self) -> int:
        return self.variable.dimension


class PointCollection(DataCollection):
    """
    Class storing all information for a point, including dataset, variable, time, position over time, etc.
    """
    def __init__(self, dataset: Dataset, variable: Variable, time: TIME, time_stamps: TIME_STAMPS, title_prefix: str,
                 title_suffix: str, data_in_time: POINT_IN_TIME):
        # Validate parameters
        if len(data_in_time) != len(time_stamps):
            raise ValueError('The length of the data in time must be equal to the length of the time stamps.')

        super().__init__(dataset, variable, time, time_stamps, title_prefix, title_suffix)
        self.data_in_time = data_in_time

    def get_time_data(self, time_index: int) -> POINT:
        return self.data_in_time[time_index]

    def get_limits(self) -> LIMITS:
        """
        The spatial limits of the point. These are the maximal limits over time.

        Returns:
            The limits.
        """
        latitudes, longitudes = np.transpose(np.array(self.data_in_time))
        return np.min(latitudes), np.max(latitudes), np.min(longitudes), np.max(longitudes)

    def get_dimension(self) -> int:
        return 2


class PathCollection(DataCollection):
    """
    Class storing all information for a path, including dataset, variable, time, path points over time, etc.
    """
    def __init__(self, dataset: Dataset, variable: Variable, time: TIME, time_stamps: TIME_STAMPS, title_prefix: str,
                 title_suffix: str, data_in_time: PATH_IN_TIME):
        # Validate parameters
        if len(data_in_time) != len(time_stamps):
            raise ValueError('The length of the data in time must be equal to the length of the time stamps.')

        super().__init__(dataset, variable, time, time_stamps, title_prefix, title_suffix)
        self.data_in_time = data_in_time

    def get_time_data(self, time_index: int) -> PATH:
        return self.data_in_time[time_index]

    def get_limits(self) -> LIMITS:
        """
        The spatial limits of the point. These are the maximal limits over time.

        Returns:
            The limits.
        """
        limits = list()
        for path in self.data_in_time:
            ex = path.get_extents()
            limits.append((ex.ymin, ex.ymax, ex.xmin, ex.xmax))

        return maximal_limits(tuple(limits))

    def get_dimension(self) -> int:
        return 2

