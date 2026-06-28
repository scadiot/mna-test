import math


class DCSource:
    """Source de tension ou de courant continu (valeur constante)."""

    def __init__(self, amplitude):
        self.amplitude = amplitude

    def voltage(self, t):
        return self.amplitude


class SineSource:
    """Source sinusoïdale : A * sin(2π * f * t + φ)."""

    def __init__(self, amplitude, frequency, phase=0.0):
        self.amplitude = amplitude
        self.frequency = frequency
        self.phase = phase

    def voltage(self, t):
        return self.amplitude * math.sin(2 * math.pi * self.frequency * t + self.phase)


class PulseSource:
    """Impulsion rectangulaire unique entre t_start et t_end."""

    def __init__(self, amplitude, t_start, t_end):
        self.amplitude = amplitude
        self.t_start = t_start
        self.t_end = t_end

    def voltage(self, t):
        return self.amplitude if self.t_start <= t <= self.t_end else 0.0


class SquareSource:
    """Signal créneau périodique avec rapport cyclique (duty_cycle)."""

    def __init__(self, amplitude, frequency, duty_cycle=0.5):
        self.amplitude = amplitude
        self.frequency = frequency
        self.duty_cycle = duty_cycle

    def voltage(self, t):
        # position dans la période courante (entre 0 et 1)
        period = 1.0 / self.frequency
        position = (t % period) / period
        return self.amplitude if position < self.duty_cycle else 0.0
