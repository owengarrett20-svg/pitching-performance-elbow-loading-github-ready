"""The planar teaching calculation must preserve direction and respect time."""

import numpy as np
import pytest

from pitching.measurement_lessons import angular_speed_from_planar_demo


@pytest.mark.parametrize("speed", [120.0, -120.0])
def test_planar_rate_preserves_signed_rotation_across_angle_wrap(speed):
    times = np.array([0.0, 0.1, 0.25, 0.5, 0.8])
    continuous = 175.0 + speed * times
    wrapped = (continuous + 180.0) % 360.0 - 180.0
    np.testing.assert_allclose(angular_speed_from_planar_demo(wrapped, times), speed, atol=1e-10)


def test_nonuniform_time_derivative_of_smooth_planar_rotation():
    times = np.array([0.0, 0.05, 0.2, 0.45, 0.7, 1.0])
    angle = 15 + 30 * times + 10 * times**2
    np.testing.assert_allclose(
        angular_speed_from_planar_demo(angle, times), 30 + 20 * times, atol=1e-10
    )


@pytest.mark.parametrize("times", [[0, 0, 1], [0, 2, 1], [2, 1, 0]])
def test_ambiguous_or_reversed_timing_is_rejected(times):
    with pytest.raises(ValueError, match="strictly increasing"):
        angular_speed_from_planar_demo([0, 10, 20], times)


@pytest.mark.parametrize(
    ("angles", "times"),
    [([0, np.nan, 20], [0, 1, 2]), ([0, 10, 20], [0, np.inf, 2])],
)
def test_missing_or_nonfinite_samples_are_not_filled(angles, times):
    with pytest.raises(ValueError, match="finite"):
        angular_speed_from_planar_demo(angles, times)


@pytest.mark.parametrize(
    ("angles", "times"), [([0, 10], [0, 1]), ([0, 10, 20], [0, 1]), ([[0, 10, 20]], [0, 1, 2])]
)
def test_insufficient_or_misaligned_samples_are_rejected(angles, times):
    with pytest.raises(ValueError, match="one-dimensional"):
        angular_speed_from_planar_demo(angles, times)
