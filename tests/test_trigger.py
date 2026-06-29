import math
from ui.trigger import compute_trigger_window


def test_rising_edge_detected():
    # Rampe : 0,1,2,...,9 ; level=4.5 → front montant unique à l'indice 5
    history = [float(i) for i in range(10)]
    win = compute_trigger_window(history, width=3, level=4.5)
    assert win == (5, 8)


def test_most_recent_eligible_edge_chosen():
    # Deux fronts montants (carré) ; on retient le plus récent dont start+width <= len
    # history index :   0  1  2  3  4  5  6  7  8  9 10 11
    history = [-1.0, -1.0, 1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0, -1.0, -1.0]
    # fronts montants à i=2 et i=7 (history[i-1] < 0 <= history[i])
    # width=3 → max_start = 12-3 = 9 ; le plus récent éligible est i=7
    win = compute_trigger_window(history, width=3, level=0.0)
    assert win == (7, 10)


def test_edge_too_recent_falls_back_to_earlier():
    # Front montant à i=2 et i=10 ; width=4 → max_start=8, donc i=10 inéligible, on prend i=2
    history = [-1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0]
    win = compute_trigger_window(history, width=4, level=0.0)
    assert win == (2, 6)


def test_no_edge_returns_none():
    history = [5.0] * 20  # signal continu plat
    assert compute_trigger_window(history, width=5, level=5.0) is None


def test_rising_edge_too_recent_returns_none():
    history = [1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0]
    # Le seul front montant à i=4 (history[3]=-1.0 < 0.0 <= history[4]=1.0) est inéligible car trop récent pour width=6 → max_start=2
    assert compute_trigger_window(history, width=6, level=0.0) is None


def test_buffer_shorter_than_width_returns_none():
    assert compute_trigger_window([1.0, 2.0], width=5, level=1.5) is None


def test_phase_stability_under_shift():
    # Sinusoïde : un décalage arbitraire du buffer donne la même phase de départ
    def sine_buf(start, n):
        return [math.sin(2 * math.pi * (start + k) / 50.0) for k in range(n)]
    buf_a = sine_buf(0, 200)
    buf_b = sine_buf(7, 200)  # décalé de 7 échantillons
    win_a = compute_trigger_window(buf_a, width=80, level=0.0)
    win_b = compute_trigger_window(buf_b, width=80, level=0.0)
    assert win_a is not None and win_b is not None
    # La valeur au début de la fenêtre est proche de 0 et montante dans les deux cas
    for buf, (start, _end) in ((buf_a, win_a), (buf_b, win_b)):
        assert abs(buf[start]) < 0.15
        assert buf[start] > buf[start - 1]
