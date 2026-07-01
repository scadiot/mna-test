import inspect
import ui.combined_panel as cp


def test_widget_exposes_interface():
    assert hasattr(cp, "CombinedGraphWidget")
    for name in ("set_meters", "update"):
        assert callable(getattr(cp.CombinedGraphWidget, name))

    sig = inspect.signature(cp.CombinedGraphWidget.update)
    assert list(sig.parameters) == ["self", "histories", "comp_objects", "dt"]
