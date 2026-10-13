"""Build a local audit viewer and bind its evidence to actual source files."""
from html import escape
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compare_visual_reconstruction import export_comparison

OUT = ROOT / "outputs/token-flow-audit-20261014"


def main():
    export_comparison(OUT / "token-01/reference.png", OUT / "new-reconstruction.png",
                      OUT / "token-01/after.png", OUT / "controlled-comparison")
    results = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    sections = []
    for result in results:
        slide = result["slide"]
        before, after = (result["metrics"][name] for name in ("before", "after"))
        cards = ''.join(f'<figure><img src="{slide}/{file}.png" alt="{label}"><figcaption>{label}</figcaption></figure>'
                        for file, label in (("reference", "真实生成设计图"), ("before", "历史实际还原"),
                                            ("after", "校准后" if slide == "token-01" else "当前播放器，未逐页校准")))
        sections.append(f'''<section><h2>{escape(slide)}</h2><div class="grid">{cards}</div>
<p>前景 MAE {before['foreground_mae']:.2f} → {after['foreground_mae']:.2f}；IoU {before['foreground_iou']:.3f} → {after['foreground_iou']:.3f}。指标诊断空间与色调，不能当审美评分。</p>
<details><summary>滑动检查目标图与实际还原</summary><div class="compare"><img src="{slide}/reference.png" alt="目标图"><img class="top" src="{slide}/after.png" alt="实际还原"></div><label>实际还原覆盖范围 <input type="range" min="0" max="100" value="50" oninput="this.closest('details').querySelector('.top').style.clipPath='inset(0 '+(100-this.value)+'% 0 0)'"></label></details>
<p><a href="{slide}/overlay-after.png">50%叠加图</a> · <a href="{slide}/review.json">真实静态检查</a> · <a href="{slide}/after.scene.json">实际场景</a></p></section>''')
    document = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Token 流程审核与前后对照</title>
<style>body{margin:0;background:#f4f4f4;color:#222;font:16px/1.7 system-ui}main{max-width:1500px;margin:auto;padding:28px}section{background:white;padding:24px;margin:28px 0}h1{font-size:30px}h2{font-size:23px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}figure{margin:0}img{max-width:100%;display:block}figcaption{margin:8px 0}a{color:#245b93}.verdict{border-left:5px solid #ab5a23;background:#fff5e9;padding:18px}.compare{position:relative}.compare>img{width:100%}.compare .top{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}input{width:240px}details{padding:12px 0}pre{white-space:pre-wrap;font:15px/1.8 system-ui}@media(max-width:850px){.grid{grid-template-columns:1fr}main{padding:12px}}</style>
<main><h1>什么是 Token：生图 → 还原流程审核</h1><p>2026-10-14 · 实际图片、共享播放器和有保留样本的前后对照</p>
<p class="verdict">局部优化有效，完整高保真闭环尚未通过。首个页面同运行时控制 MAE下降约17.5%；动态几何错误对象43→0。四个保留页面未一致改善，新生图仍被模板改变构图和主体。</p>
<p><a href="../../docs/research/2026-10-14-token-flow-audit/report.md">详细审核报告</a> · <a href="results.json">五页视觉量测</a> · <a href="motion-evidence-before.json">动态修复前</a> · <a href="motion-evidence.json">动态修复后</a> · <a href="controlled-comparison/comparison.png">同运行时三栏控制对照</a></p>'''
    document += ''.join(sections)
    document += '''<section><h2>真实新增生图复测</h2><p>ToAPIs gpt-image-2-vip · low/1K · 实际1536×864；历史模型/尺寸不同，不作为Prompt A/B。设计图中的主体、标签和标题容器没有被当前模板完整保留。</p><div class="grid"><figure><img src="new-generated-design.png" alt="本轮新生成设计图"><figcaption>本轮真实生图</figcaption></figure><figure><img src="new-reconstruction.png" alt="图片完成后实际模板还原"><figcaption>生图完成后的真实模板渲染，复用独立素材</figcaption></figure><figure><img src="reference-package/layout-guide.png" alt="实际发送给模型的布局参考"><figcaption>实际发送的确定性布局guide</figcaption></figure></div><p>此复测失败项已进入报告，未给予正式作品批准。</p></section>'''
    report = (ROOT / "docs/research/2026-10-14-token-flow-audit/report.md").read_text(encoding="utf-8")
    document += '<section><h2>完整审核报告</h2><pre>' + escape(report) + '</pre></section></main></html>'
    (OUT / "index.html").write_text(document, encoding="utf-8")
    sources = ["html_layout_reference.py", "html_reference_package.py", "html_design_candidates.py",
               "html_production_service.py", "html_engine/visual/renderer.cjs", "html_engine/visual/preview/player.js"]
    evidence = {"source_sha256": {file: hashlib.sha256((ROOT / file).read_bytes()).hexdigest() for file in sources},
                "actual_new_image_size": list(Image.open(OUT / "new-generated-design.png").size),
                "new_image_sha256": hashlib.sha256((OUT / "new-generated-design.png").read_bytes()).hexdigest(),
                "formal_approval": False, "formal_export": False, "paid_image_calls_this_audit": 1, "cost": None}
    (OUT / "audit-manifest.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
