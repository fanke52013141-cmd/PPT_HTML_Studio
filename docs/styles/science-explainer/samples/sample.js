/* P02 visual review only: fixed states, no scene compiler or audio clock. */
const slide = document.querySelector('.slide');
const viewport = document.querySelector('.viewport');
const original = [document.querySelector('#evaporation-body').textContent, document.querySelector('#condensation-body').textContent];
function setStage(stage) {
  if (!['initial', 'first', 'compare', 'final'].includes(stage)) throw new Error('Unknown review stage');
  slide.dataset.stage = stage;
  for (const button of document.querySelectorAll('button[data-stage]')) {
    const selected = button.dataset.stage === stage;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-pressed', String(selected));
  }
}
function fit() {
  const scale = Math.min(1, Math.max(0.1, (viewport.clientWidth - 52) / 1920));
  slide.style.transform = `scale(${scale})`;
  viewport.style.height = `${1080 * scale + 52}px`;
}
for (const button of document.querySelectorAll('button[data-stage]')) button.addEventListener('click', () => setStage(button.dataset.stage));
document.querySelector('#long-copy').addEventListener('click', () => {
  const enabled = slide.classList.toggle('long-copy');
  document.querySelector('#evaporation-body').textContent = enabled ? '液态水变成气态的水蒸气。水没有沸腾，也可以发生蒸发。用晾衣服这个生活例子，可以帮助理解这一过程，并区分生活现象与科学示意。' : original[0];
  document.querySelector('#condensation-body').textContent = enabled ? '空气中的水蒸气可以变成液态水。冰水杯外壁上的水滴，就是一个例子。此处用较长的说明文字，检查字体、行距和插图区域是否仍能协调。' : original[1];
  document.querySelector('#long-copy').setAttribute('aria-pressed', String(enabled));
});
window.setReviewStage = setStage;
window.addEventListener('resize', fit);
setStage('final'); fit();
