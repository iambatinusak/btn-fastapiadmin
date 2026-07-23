/* fastapiadmin — minimal JS helpers */

// Auto-clear flash messages after 4s
document.addEventListener("DOMContentLoaded", () => {
  const flash = document.getElementById("flash-msg");
  if (flash) {
    setTimeout(() => {
      flash.style.transition = "opacity 0.4s, transform 0.4s";
      flash.style.opacity = "0";
      flash.style.transform = "translateY(-6px)";
      setTimeout(() => flash.remove(), 400);
    }, 4000);
  }

  // Confirm delete with a nicer overlay instead of browser confirm()
  const deleteForms = document.querySelectorAll("[data-confirm]");
  deleteForms.forEach((form) => {
    form.addEventListener("submit", (e) => {
      const msg = form.dataset.confirm;
      if (!window.__confirmed) {
        e.preventDefault();
        showConfirm(msg, () => {
          window.__confirmed = true;
          form.submit();
        });
      }
    });
  });

  // Sidebar: mark active
  const links = document.querySelectorAll(".nav-item");
  const current = location.pathname;
  links.forEach((a) => {
    if (a.getAttribute("href") && current.startsWith(a.getAttribute("href")) &&
        a.getAttribute("href") !== "/") {
      a.classList.add("active");
    }
  });
});

function showConfirm(msg, onConfirm) {
  const overlay = document.createElement("div");
  overlay.className = "confirm-overlay";
  overlay.innerHTML = `
    <div class="confirm-box">
      <div class="confirm-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <h3 class="confirm-title">Are you sure?</h3>
      <p class="confirm-msg">${msg}</p>
      <div class="confirm-actions">
        <button class="btn btn-secondary" id="cancel-btn">Cancel</button>
        <button class="btn btn-danger-solid" id="ok-btn">Delete</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  requestAnimationFrame(() => overlay.classList.add("visible"));

  overlay.querySelector("#cancel-btn").onclick = () => overlay.remove();
  overlay.querySelector("#ok-btn").onclick = () => { overlay.remove(); onConfirm(); };
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
}
