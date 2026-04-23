def test_image_generation_kernel():
    from core.kernel import AriaKernel
    import asyncio

    k = AriaKernel()

    res = asyncio.run(
        k.handle_message("dessine un robot dans un jardin")
    )

    # test
    assert res.endswith(".png")