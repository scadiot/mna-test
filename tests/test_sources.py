import math
import pytest
from simulator.sources import DCSource, SineSource, PulseSource, SquareSource

def test_dc_source():
    """Une source DC retourne toujours la même tension."""
    src = DCSource(5.0)
    assert src.voltage(0.0) == 5.0
    assert src.voltage(100.0) == 5.0

def test_sine_source_zero_crossing():
    """Sinusoïde à t=0 doit valoir 0 (sin(0) = 0)."""
    src = SineSource(amplitude=1.0, frequency=1.0)
    assert src.voltage(0.0) == pytest.approx(0.0, abs=1e-10)

def test_sine_source_peak():
    """Sinusoïde à t=T/4 doit valoir l'amplitude."""
    src = SineSource(amplitude=3.0, frequency=2.0)  # période = 0.5 s
    assert src.voltage(0.125) == pytest.approx(3.0, abs=1e-10)

def test_sine_source_with_phase():
    """Sinusoïde avec déphasage π/2 vaut l'amplitude à t=0."""
    src = SineSource(amplitude=1.0, frequency=1.0, phase=math.pi / 2)
    assert src.voltage(0.0) == pytest.approx(1.0, abs=1e-10)

def test_pulse_before():
    src = PulseSource(amplitude=5.0, t_start=0.1, t_end=0.5)
    assert src.voltage(0.05) == 0.0

def test_pulse_during():
    src = PulseSource(amplitude=5.0, t_start=0.1, t_end=0.5)
    assert src.voltage(0.3) == 5.0

def test_pulse_after():
    src = PulseSource(amplitude=5.0, t_start=0.1, t_end=0.5)
    assert src.voltage(0.6) == 0.0

def test_square_high():
    """Premier demi-cycle → tension haute."""
    src = SquareSource(amplitude=5.0, frequency=1.0, duty_cycle=0.5)
    assert src.voltage(0.0) == 5.0
    assert src.voltage(0.49) == 5.0

def test_square_low():
    """Deuxième demi-cycle → tension basse."""
    src = SquareSource(amplitude=5.0, frequency=1.0, duty_cycle=0.5)
    assert src.voltage(0.51) == 0.0

def test_square_second_period():
    """Début de la deuxième période → retour à tension haute."""
    src = SquareSource(amplitude=5.0, frequency=1.0, duty_cycle=0.5)
    assert src.voltage(1.0) == 5.0
