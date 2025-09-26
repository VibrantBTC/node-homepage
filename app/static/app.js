function getSyncColor(percent) {
  if (percent >= 99.9) return "bg-green-500";
  if (percent >= 95) return "bg-yellow-500";
  return "bg-red-500";
}

async function copyText(text, el) {
  let ok = false;
  try {
    await navigator.clipboard.writeText(text);
    ok = true;
  } catch (e) {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "absolute";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      ok = document.execCommand("copy");
      document.body.removeChild(ta);
    } catch (e2) {
      ok = false;
    }
  }
  if (el) {
    if (ok) {
      el.classList.add("copied");
      setTimeout(() => el.classList.remove("copied"), 800);
    } else {
      const old = el.style.color;
      el.style.color = "#fca5a5";
      setTimeout(() => { el.style.color = old || ""; }, 800);
    }
  }
}

function bindCopyables() {
  document.querySelectorAll("[data-copy]").forEach(el => {
    el.addEventListener("click", () => {
      const data = el.getAttribute("data-copy");
      const text = data && data.length ? data : el.textContent.trim();
      copyText(text, el);
    });
  });
}

// Collapsible helpers
function openSection(bodyId, arrowId) {
  const body = document.getElementById(bodyId);
  const arrow = document.getElementById(arrowId);
  if (!body) return;
  const inner = body.querySelector(".collapsible-inner");
  body.classList.add("open");
  body.style.maxHeight = inner.scrollHeight + "px";
  if (arrow) arrow.classList.add("rotated");
}

function closeSection(bodyId, arrowId) {
  const body = document.getElementById(bodyId);
  const arrow = document.getElementById(arrowId);
  if (!body) return;
  const inner = body.querySelector(".collapsible-inner");
  body.style.maxHeight = inner.scrollHeight + "px";
  requestAnimationFrame(() => {
    body.style.maxHeight = "0px";
    body.classList.remove("open");
    if (arrow) arrow.classList.remove("rotated");
  });
}

function toggleSection(bodyId, arrowId) {
  const body = document.getElementById(bodyId);
  if (!body) return;
  if (body.classList.contains("open")) {
    closeSection(bodyId, arrowId);
  } else {
    openSection(bodyId, arrowId);
  }
}

function recalcHeights() {
  document.querySelectorAll(".collapsible.open").forEach(body => {
    const inner = body.querySelector(".collapsible-inner");
    body.style.maxHeight = inner.scrollHeight + "px";
  });
}
window.addEventListener("resize", recalcHeights);

// QR modal
function openQR(src) {
  const modal = document.getElementById("qrModal");
  const img = document.getElementById("qrModalImg");
  img.src = src;
  modal.classList.add("show");
  document.querySelector(".page-wrap").classList.add("blurred");
}
function closeQR() {
  const modal = document.getElementById("qrModal");
  modal.classList.remove("show");
  document.querySelector(".page-wrap").classList.remove("blurred");
}
function enableQRClicks() {
  document.querySelectorAll(".qr").forEach(img => {
    img.style.cursor = "zoom-in";
    img.addEventListener("click", (e) => {
      openQR(e.target.getAttribute("src"));
    });
  });
  const modal = document.getElementById("qrModal");
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeQR();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeQR();
  });
}

async function refreshBitcoin() {
  try {
    const res = await fetch("/api/bitcoin");
    const d = await res.json();
    if (d.error) return;

    document.getElementById("btc_version").textContent = d.version;
    document.getElementById("btc_sync_text").textContent =
      `${d.blocks} / ${d.headers} (${d.sync_percent}%)`;

    const bar = document.getElementById("btc_bar");
    bar.style.width = `${d.sync_percent}%`;
    bar.className =
      `h-2 rounded-full ${getSyncColor(d.sync_percent)} transition-all duration-500`;

    const dot = document.getElementById("btc_dot");
    dot.className =
      `w-3 h-3 rounded-full inline-block ${getSyncColor(d.sync_percent)}`;
    document.getElementById("btc_status").textContent =
      d.sync_percent >= 99.9 ? "Synced" : "Syncing";

    document.getElementById("btc_disk").textContent = d.disk_size_gb;
    document.getElementById("btc_mempool").textContent = d.mempool_mb;
    document.getElementById("btc_peers").textContent =
      `${d.connections.total} (${d.connections.inbound} in / ${d.connections.outbound} out)`;
    document.getElementById("btc_uptime").textContent = d.uptime;

    recalcHeights();
  } catch (e) {
    console.error(e);
  }
}

async function refreshFulcrum() {
  try {
    const res = await fetch("/api/fulcrum");
    const d = await res.json();
    if (d.error) return;

    // Always set version if provided
    if (typeof d.version === "string" && d.version.length) {
      const vEl = document.getElementById("fl_version");
      if (vEl) vEl.textContent = d.version;
    }

    // Bitcoin down badge
    const badge = document.getElementById("fl_btc_badge");
    if (badge) {
      if (d.bitcoin_up) badge.classList.add("hidden");
      else badge.classList.remove("hidden");
    }

    if (d.source === "disabled") return;

    if (typeof d.height === "number") {
      const syncText = `${d.height} (${d.sync_percent}%)`;
      const syncEl = document.getElementById("fl_sync_text");
      if (syncEl) syncEl.textContent = syncText;
    }

    const bar = document.getElementById("fl_bar");
    if (bar) {
      bar.style.width = `${d.sync_percent}%`;
      bar.className =
        `h-2 rounded-full ${getSyncColor(d.sync_percent)} transition-all duration-500`;
    }

    const dot = document.getElementById("fl_dot");
    if (dot) {
      dot.className =
        `w-3 h-3 rounded-full inline-block ${getSyncColor(d.sync_percent)}`;
    }

    const statusEl = document.getElementById("fl_status");
    if (statusEl) statusEl.textContent = d.status || (d.sync_percent >= 99.9 ? "Synced" : "Indexing");

    // Speeds (only present while indexing)
    const speedEl = document.getElementById("fl_speeds");
    if (speedEl) {
      if (d.speeds) {
        speedEl.textContent =
          `${d.speeds.blocks_per_sec} blk/s · ${d.speeds.txs_per_sec} tx/s · ${d.speeds.addrs_per_sec} addr/s`;
        speedEl.classList.remove("hidden");
      } else {
        speedEl.classList.add("hidden");
      }
    }

    recalcHeights();
  } catch (e) {
    console.error(e);
  }
}

setInterval(() => {
  refreshBitcoin();
  refreshFulcrum();
}, 30000);

window.addEventListener("load", () => {
  refreshBitcoin();
  refreshFulcrum();
  bindCopyables();
  enableQRClicks();
  openSection("btc_body", "btc_arrow");
});
