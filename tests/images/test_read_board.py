# tests/images/test_read_board.py
#
# Sprint 59, tronçon 01 : ImageRouter.read_board, repli sur grille non conforme.

from llm.image_router import ImageRouter

_ROWS = ["r.bqkb.r", "pp...ppp", "..n..n..", "..pp....",
         "..B.....", "..NP.N..", "PPP..PPP", "R.BQK..R"]


def _fake(answer):
    class FakeVision:
        def describe(self, image, prompt):
            return answer

    return {"provider": "fake", "client": lambda **kw: FakeVision()}


def test_read_board_skips_invalid_and_cleans_fences():
    fenced = "```\n" + "\n".join(_ROWS) + "\n```"
    router = ImageRouter(board_table=[_fake("Voici l'échiquier."), _fake(fenced)])
    assert router.read_board("img.jpg") == _ROWS


def test_read_board_all_fail_returns_none():
    router = ImageRouter(board_table=[_fake("rien")])
    assert router.read_board("img.jpg") is None
