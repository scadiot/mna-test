import threading
from shared_state import SharedState

def test_write_and_read():
    """Vérifie que write() puis read() retournent les bonnes valeurs."""
    state = SharedState()
    state.init_histories(["VM1"], history_size=100)
    state.write(
        node_voltages={"N1": 5.0},
        comp_states={"R1": {"voltage": 5.0, "current": 0.005}},
        history_updates={"VM1": 3.14},
    )
    data = state.read()
    assert data["node_voltages"]["N1"] == 5.0
    assert data["comp_states"]["R1"]["voltage"] == 5.0
    assert 3.14 in data["histories"]["VM1"]

def test_history_maxlen():
    """Vérifie que l'historique respecte la taille maximale."""
    state = SharedState()
    state.init_histories(["VM1"], history_size=3)
    for i in range(10):
        state.write({}, {}, {"VM1": float(i)})
    data = state.read()
    assert len(data["histories"]["VM1"]) == 3
    assert data["histories"]["VM1"] == [7.0, 8.0, 9.0]

def test_thread_safety():
    """Vérifie l'absence d'erreurs avec écriture et lecture simultanées."""
    state = SharedState()
    state.init_histories(["VM1"], history_size=1000)
    errors = []

    def writer():
        for i in range(200):
            state.write({"N1": float(i)}, {}, {"VM1": float(i)})

    def reader():
        for _ in range(200):
            try:
                state.read()
            except Exception as e:
                errors.append(str(e))

    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader)
    t1.start(); t2.start()
    t1.join(); t2.join()
    assert not errors

def test_set_error():
    """Vérifie que set_error() arrête la simulation et stocke le message."""
    state = SharedState()
    state.running = True
    state.set_error("matrice singulière")
    data = state.read()
    assert data["error"] == "matrice singulière"
    assert not state.running
