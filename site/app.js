// Copy buttons and the before/after comparison.
document.querySelectorAll("[data-copy]").forEach((btn) => {
  const label = btn.textContent;
  btn.addEventListener("click", async () => {
    const text = document.querySelector(btn.dataset.copy).textContent;
    try {
      await navigator.clipboard.writeText(text);
      btn.dataset.done = "";
      btn.textContent = btn.dataset.doneLabel || "Copied";
      setTimeout(() => { btn.textContent = label; delete btn.dataset.done; }, 1600);
    } catch {
      const range = document.createRange();
      range.selectNodeContents(document.querySelector(btn.dataset.copy));
      getSelection().removeAllRanges();
      getSelection().addRange(range);
    }
  });
});

document.querySelectorAll(".compare").forEach((box) => {
  const input = box.querySelector("input");
  const set = () => box.style.setProperty("--cut", input.value + "%");
  input.addEventListener("input", set);
  set();
});
