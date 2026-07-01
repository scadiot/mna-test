import math
import pytest
from ui.plot_utils import time_unit, shared_trigger_window, build_combined_series
from simulator.components import Voltmeter, Ammeter


def test_time_unit_seconds():
    assert time_unit(2.0) == ("s", 1.0)


def test_time_unit_milliseconds():
    assert time_unit(5e-3) == ("ms", 1e3)


def test_time_unit_microseconds():
    assert time_unit(5e-6) == ("µs", 1e6)


def test_time_unit_nanoseconds():
    assert time_unit(5e-9) == ("ns", 1e9)


def test_shared_window_off_returns_none():
    assert shared_trigger_window([1.0, 2.0, 3.0, 4.0], trigger_on=False) is None


def test_shared_window_empty_returns_none():
    assert shared_trigger_window([], trigger_on=True) is None


def test_shared_window_on_matches_compute():
    # Rampe 0..19 ; width = 20//2 = 10 ; level = moyenne = 9.5
    # front montant à i=10 (history[9]=9 < 9.5 <= history[10]=10) ; max_start = 10
    hist = [float(i) for i in range(20)]
    assert shared_trigger_window(hist, trigger_on=True) == (10, 20)


def test_shared_window_preserves_phase_offset():
    # Deux sinusoïdes échantillonnées sur la MÊME base de temps, l'une déphasée.
    # La fenêtre calculée sur la référence, appliquée aux deux, conserve l'écart.
    n = 200
    ref = [math.sin(2 * math.pi * k / 50.0) for k in range(n)]
    other = [math.sin(2 * math.pi * k / 50.0 + math.pi / 2) for k in range(n)]
    win = shared_trigger_window(ref, trigger_on=True)
    assert win is not None
    start, end = win
    ref_slice = ref[start:end]
    other_slice = other[start:end]
    # même longueur, indices alignés → l'écart de phase est préservé
    assert len(ref_slice) == len(other_slice)
    # à l'index 0 de la fenêtre : ref ≈ 0 montant, other ≈ cos(0) = 1
    assert abs(ref_slice[0]) < 0.15
    assert other_slice[0] > 0.9


def test_build_series_labels_and_units():
    comp_objects = {
        "V1": Voltmeter("V1", "a", "b"),
        "A1": Ammeter("A1", "b", "c"),
    }
    histories = {"V1": [1.0, 2.0, 3.0], "A1": [0.1, 0.2, 0.3]}
    series = build_combined_series(histories, comp_objects, window=None)
    assert series == [("V1 (V)", [1.0, 2.0, 3.0]), ("A1 (A)", [0.1, 0.2, 0.3])]


def test_build_series_applies_window():
    comp_objects = {"V1": Voltmeter("V1", "a", "b")}
    histories = {"V1": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]}
    series = build_combined_series(histories, comp_objects, window=(2, 5))
    assert series == [("V1 (V)", [2.0, 3.0, 4.0])]


def test_build_series_skips_empty_and_non_recording():
    class Dummy:
        records_history = False
    comp_objects = {
        "V1": Voltmeter("V1", "a", "b"),
        "V2": Voltmeter("V2", "c", "d"),  # historique absent
        "R1": Dummy(),                     # n'enregistre pas
    }
    histories = {"V1": [1.0], "V2": []}
    series = build_combined_series(histories, comp_objects, window=None)
    assert series == [("V1 (V)", [1.0])]
