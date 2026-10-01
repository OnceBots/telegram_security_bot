from security_bot.captcha import build_keyboard, create_challenge

def test_challenge():
    c=create_challenge(); assert len(c.options)==4; assert c.options.count(c.correct)==1; assert c.a+c.b==c.correct

def test_callbacks_under_64_chars():
    c=create_challenge(); k=build_keyboard("abc123def456",c.options)
    callbacks=[b.callback_data for row in k.inline_keyboard for b in row]
    assert all(x.startswith("chk:abc123def456:") for x in callbacks)
    assert max(map(len,callbacks))<64
