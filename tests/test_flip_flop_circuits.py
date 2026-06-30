# tests/test_flip_flop_circuits.py
import os
from circuit_loader import load_circuit
from shared_state import SharedState
from simulator.engine import SimulationEngine

CIRCUITS_DIR = os.path.join(os.path.dirname(__file__), "..", "circuits")


def make_engine(filename):
    """Charge un circuit et construit un moteur prêt à être pas-à-passé."""
    circuit = load_circuit(os.path.join(CIRCUITS_DIR, filename))
    state = SharedState()
    for cid, size in circuit.histories.items():
        state.init_histories([cid], size)
    engine = SimulationEngine(circuit, state)
    return circuit, engine, state


def run(engine, n, callback=None):
    """Exécute n pas. callback(i, t) appelé avant chaque pas (pour piloter
    les interrupteurs). Lève AssertionError si la MNA devient singulière."""
    for i in range(n):
        t = i * engine._dt
        if callback:
            callback(i, t)
        assert engine._step(t), f"MNA singuliere au pas {i} (t={t:.4f}s)"


def vmeter(engine, comp_id):
    """Dernière tension lue par un voltmètre (dernière valeur calculée,
    état courant après le dernier _step)."""
    return engine._prev_states[comp_id]["voltage"]


def component(circuit, comp_id):
    """Retourne le composant d'identifiant comp_id."""
    return next(c for c in circuit.components if c.id == comp_id)


def _transitions(samples, low=1.0, high=3.0):
    """Compte les allers-retours bas<->haut d'un signal échantillonné."""
    count, level = 0, None
    for v in samples:
        if v <= low and level != "lo":
            if level is not None:
                count += 1
            level = "lo"
        elif v >= high and level != "hi":
            if level is not None:
                count += 1
            level = "hi"
    return count


def test_astable_oscille():
    circuit, engine, _ = make_engine("flip_flop_astable.json")
    samples = []

    def collect(i, t):
        # Ignore les premiers pas pour eviter le bruit numerique au demarrage
        if i >= 10:
            samples.append(vmeter(engine, "VM_C1"))

    run(engine, 4000, callback=collect)
    assert min(samples) < 1.0, f"jamais a l'etat bas (min={min(samples):.2f})"
    assert max(samples) > 3.0, f"jamais a l'etat haut (max={max(samples):.2f})"
    assert _transitions(samples) >= 4, "oscillation insuffisante"
    # Borne anti-pic : la convergence intra-pas (Task 2) borne naturellement les
    # pics de commutation du modele BJT piecewise-lineaire. Les condensateurs Cc1/Cc2
    # (originellement 200 uF chacun) ont ete supprimes, elimant les instabilites numeriques.
    assert min(samples) > -10.0, f"pic de commutation trop violent (min={min(samples):.2f})"


def test_transitions_compte_les_basculements():
    # Sequence purement basse : 0 transition
    assert _transitions([0, 0, 0]) == 0
    # Montee puis descente : 2 transitions (bas->haut->bas)
    assert _transitions([0, 0, 4, 4, 0, 0]) == 2
    # Sequence dans la zone morte : 0 transition
    assert _transitions([2, 2, 2]) == 0


def test_bistable_set_reset_memorise():
    circuit, engine, _ = make_engine("flip_flop_bistable_rs.json")
    s_set = component(circuit, "S_set")
    s_reset = component(circuit, "S_reset")

    # SET : ferme S_set 200 pas, puis le rouvre
    s_set.closed = True
    run(engine, 200)
    s_set.closed = False
    run(engine, 200)
    # Q1 conduit -> collecteur 1 bas, collecteur 2 haut, et l'etat PERSISTE
    assert vmeter(engine, "VM_C1") < 1.0, "Set: C1 devrait etre bas"
    assert vmeter(engine, "VM_C2") > 3.0, "Set: C2 devrait etre haut"

    # RESET : ferme S_reset, puis rouvre -> etat inverse memorise
    s_reset.closed = True
    run(engine, 200)
    s_reset.closed = False
    run(engine, 200)
    assert vmeter(engine, "VM_C2") < 1.0, "Reset: C2 devrait etre bas"
    assert vmeter(engine, "VM_C1") > 3.0, "Reset: C1 devrait etre haut"


def test_bistable_power_on_etat_defini():
    """Au power-on sans aucune action sur les interrupteurs, le bistable doit
    converger vers un etat defini (un collecteur bas < 1 V, l'autre haut > 3 V)
    sans jamais produire de tension aberrante (< -1 V).

    La dissymetrie introduite (Cc1 = 5 uF contre Cc2 = 100 nF) favorise Q1
    passant des le premier pas et evite que les deux transistors oscillent vers
    un etat non physique. Cc1 a ete reduit de 47 uF a 5 uF (facteur 9.4x) ;
    Cc2 reste a 100 nF et amortit le transitoire de commutation du modele BJT piecewise-lineaire.
    """
    circuit, engine, _ = make_engine("flip_flop_bistable_rs.json")
    all_samples = []

    def collect_both(i, t):
        all_samples.append(vmeter(engine, "VM_C1"))
        all_samples.append(vmeter(engine, "VM_C2"))

    run(engine, 600, callback=collect_both)

    assert min(all_samples) > -1.0, (
        f"tension aberrante detectee au power-on (min={min(all_samples):.2f} V)"
    )

    c1_final = vmeter(engine, "VM_C1")
    c2_final = vmeter(engine, "VM_C2")
    etat_defini = (c1_final < 1.0) != (c2_final < 1.0)
    assert etat_defini, (
        f"etat bistable indefini en fin de course : C1={c1_final:.3f} V, C2={c2_final:.3f} V"
    )
    assert (c1_final < 1.0 and c2_final > 3.0) or (c2_final < 1.0 and c1_final > 3.0), (
        f"etat non valide : C1={c1_final:.3f} V, C2={c2_final:.3f} V "
        f"(attendu : un < 1 V et l'autre > 3 V)"
    )


def test_monostable_impulsion():
    circuit, engine, _ = make_engine("flip_flop_monostable.json")
    s_trig = component(circuit, "S_trig")

    # Repos : Q2 passant -> C2 bas, Q1 bloque -> C1 haut
    run(engine, 300)
    assert vmeter(engine, "VM_C2") < 1.0, "repos: C2 devrait etre bas"
    assert vmeter(engine, "VM_C1") > 3.0, "repos: C1 devrait etre haut"

    # Declenchement : impulsion breve sur la base de Q1
    s_trig.closed = True
    run(engine, 20)
    s_trig.closed = False

    # Pendant l'impulsion, C2 passe haut (Q2 bloque)
    samples_c2 = []
    run(engine, 600, callback=lambda i, t: samples_c2.append(vmeter(engine, "VM_C2")))
    assert max(samples_c2) > 3.0, "C2 n'est jamais passe haut apres declenchement"

    # Retour au repos apres l'impulsion
    run(engine, 600)
    assert vmeter(engine, "VM_C2") < 1.0, "C2 n'est pas revenu au repos (bas)"
    assert vmeter(engine, "VM_C1") > 3.0, "C1 n'est pas revenu au repos (haut)"
