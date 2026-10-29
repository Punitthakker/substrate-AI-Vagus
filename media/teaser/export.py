import asyncio, sys, base64, subprocess
from playwright.async_api import async_playwright
R = '/home/claude/substrate-teaser'
mode = sys.argv[1]   # sheet <t,t,...> | audio | video <out.mp4> <fps>

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1080, 'height': 1920})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        await pg.goto(f'file://{R}/teaser.html'); await pg.wait_for_timeout(700)
        await pg.evaluate('document.fonts.ready'); await pg.wait_for_timeout(200)
        if mode == 'sheet':
            for t in [float(x) for x in sys.argv[2].split(',')]:
                await pg.evaluate(f'window.__reel.seek({t})')
                await pg.screenshot(path=f'{R}/out/f_{t:05.1f}.png')
        elif mode == 'audio':
            s = await pg.evaluate('window.__reel.audio()')
            open(f'{R}/out/score.wav', 'wb').write(base64.b64decode(s))
        elif mode == 'video':
            out, fps = sys.argv[2], int(sys.argv[3]); D = 80
            ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(fps), '-c:v', 'mjpeg', '-i', '-',
                                   '-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-crf', '16', out], stdin=subprocess.PIPE)
            n = int(D * fps)
            for i in range(n):
                await pg.evaluate(f'window.__reel.seek({i / fps})')
                ff.stdin.write(await pg.screenshot(type='jpeg', quality=93))
                if i % 150 == 0: print('frame', i, '/', n, flush=True)
            ff.stdin.close(); ff.wait()
        print(mode, 'errors:', errs[:6], flush=True)
        await b.close()

asyncio.run(main())
