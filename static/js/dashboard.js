document.addEventListener('DOMContentLoaded', () => {

  // ---------- HELPERS ----------
  function statusBadge(status) {
    const cls = status === 'Active' ? 'active' : status === 'Overdue' ? 'overdue' : 'returned';
    return `<span class="badge ${cls}">${status}</span>`;
  }

  function showMessage(text, isError) {
    const el = document.getElementById('scan-message');
    if (!el) return;
    el.textContent = text;
    el.className = 'message ' + (isError ? 'error' : 'success');
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 4000);
  }

  // ---------- DASHBOARD STATS ----------
  function loadStats() {
    fetch('/api/my-stats')
      .then(r => r.json())
      .then(data => {
        if (!data.success) return;
        document.getElementById('stat-total-borrowed').textContent = data.stats.total_borrowed;
        document.getElementById('stat-pending').textContent        = data.stats.pending_return;
        document.getElementById('stat-returned').textContent       = data.stats.returned;
        document.getElementById('stat-available').textContent      = data.stats.available_tools;
      })
      .catch(() => {});
  }

  // ---------- SCAN CENTER DROPDOWNS ----------
  function loadToolDropdowns() {
    fetch('/api/tools/available')
      .then(r => r.json())
      .then(data => {
        const sel = document.getElementById('borrow-tool-select');
        if (!sel) return;
        sel.innerHTML = '';
        if (!data.tools || data.tools.length === 0) {
          sel.innerHTML = '<option value="">No tools available</option>';
        } else {
          data.tools.forEach(t => {
            sel.innerHTML += `<option value="${t.tool_id}">${t.tool_name} (${t.category})</option>`;
          });
        }
      })
      .catch(() => {});

    fetch('/api/my-tools')
      .then(r => r.json())
      .then(data => {
        const sel = document.getElementById('return-tool-select');
        if (!sel) return;
        sel.innerHTML = '';
        if (!data.tools || data.tools.length === 0) {
          sel.innerHTML = '<option value="">Nothing to return</option>';
        } else {
          data.tools.forEach(t => {
            sel.innerHTML += `<option value="${t.tool_id}">${t.tool_name}</option>`;
          });
        }
      })
      .catch(() => {});
  }

const btnBorrow = document.getElementById('btn-borrow');
  if (btnBorrow) {
    btnBorrow.addEventListener('click', () => {
      const toolId = document.getElementById('borrow-tool-select').value;
      const qty = parseInt(document.getElementById('borrow-qty-input')?.value, 10) || 1;
      if (!toolId) return;
      fetch('/api/borrow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_id: toolId, quantity: qty })
      })
        .then(r => r.json())
        .then(data => {
          showMessage(data.message, !data.success);
          if (data.success) loadToolDropdowns();
        });
    });
  }


  const btnReturn = document.getElementById('btn-return');
  if (btnReturn) {
    btnReturn.addEventListener('click', () => {
      const toolId = document.getElementById('return-tool-select').value;
      if (!toolId) return;
      fetch('/api/return', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_id: toolId })
      })
        .then(r => r.json())
        .then(data => {
          showMessage(data.message, !data.success);
          if (data.success) loadToolDropdowns();
        });
    });
  }

  // ---------- MY TOOLS CARDS ----------
  function dueSoonInfo(dueDateStr, status) {
    if (!dueDateStr || dueDateStr === 'None' || status === 'Returned') return null;
    const due   = new Date(dueDateStr);
    const today = new Date();
    today.setHours(0,0,0,0);
    const diffDays = Math.ceil((due - today) / (1000 * 60 * 60 * 24));

    if (status === 'Overdue' || diffDays < 0) {
      return { text: '⚠ Overdue', cls: 'due-overdue' };
    }
    if (diffDays <= 5) {
      return { text: `⏰ Due in ${diffDays} day${diffDays === 1 ? '' : 's'}`, cls: 'due-soon' };
    }
    return null;
  }

  function loadMyTools() {
    fetch('/api/my-tools')
      .then(r => r.json())
      .then(data => {
        const wrap = document.getElementById('mytools-body');
        if (!wrap) return;
        if (!data.tools || data.tools.length === 0) {
          wrap.innerHTML = '<div class="empty-row">No tools currently borrowed.</div>';
          return;
        }
        wrap.innerHTML = data.tools.map(t => {
          const alertInfo = dueSoonInfo(t.due_date, t.status);
          return `
          <div class="tool-card">
            <div class="tool-card-head">
              <div class="tool-card-icon">🧰</div>
              <div>
                <div class="tool-card-name">${t.tool_name}</div>
                <div class="tool-card-meta">Tool ID: ${t.tool_id}</div>
              </div>
            </div>
            <div class="tool-card-rows">
              <div class="tool-card-row"><span class="k">Borrowed</span><span class="v">${t.borrow_date}</span></div>
              <div class="tool-card-row"><span class="k">Time</span><span class="v">${t.borrow_time}</span></div>
              <div class="tool-card-row"><span class="k">Due Date</span><span class="v">${t.due_date || '—'}</span></div>
            </div>
            ${alertInfo ? `<div class="due-alert ${alertInfo.cls}">${alertInfo.text}</div>` : ''}
            <div class="tool-card-foot">
              ${statusBadge(t.status)}
            </div>
          </div>
        `;
        }).join('');
      })
      .catch(() => {});
  }

  // ---------- HISTORY TABLE ----------
  function loadHistory() {
    fetch('/api/my-history')
      .then(r => r.json())
      .then(data => {
        const body = document.getElementById('history-body');
        if (!body) return;
        if (!data.history || data.history.length === 0) {
          body.innerHTML = '<tr><td colspan="6" class="empty-row">No transactions yet.</td></tr>';
          return;
        }
        body.innerHTML = data.history.map(t => `
          <tr>
            <td>${t.tool_name}</td>
            <td>${t.borrow_date}</td>
            <td>${t.borrow_time}</td>
            <td>${t.return_date || '—'}</td>
            <td>${t.return_time || '—'}</td>
            <td>${statusBadge(t.status)}</td>
          </tr>
        `).join('');
      })
      .catch(() => {});
  }

  // ---------- QR CAMERA SCANNER ----------
  let html5QrCode = null;
  let scanMode = null;   // 'borrow' | 'return'
  let scanLocked = false; // prevents multiple decode fires while success animation plays

  function setScannerState(state, text) {
    const frame  = document.querySelector('.scanner-frame');
    const status = document.getElementById('scan-status');
    if (frame) frame.classList.remove('success', 'error');
    if (status) status.classList.remove('success', 'error');
    if (state && frame)  frame.classList.add(state);
    if (state && status) status.classList.add(state);
    if (status && text) status.textContent = text;
  }

  function stopScanner() {
    if (html5QrCode) {
      html5QrCode.stop().then(() => {
        html5QrCode.clear();
        const wrap = document.getElementById('qr-reader-wrap');
        if (wrap) wrap.style.display = 'none';
      }).catch(() => {});
    }
  }

  function startScanner(mode) {
    scanMode = mode;
    scanLocked = false;
    const wrap = document.getElementById('qr-reader-wrap');
    const title = document.getElementById('qr-reader-title');
    if (!wrap) return;
    wrap.style.display = 'block';
    title.textContent = mode === 'borrow' ? 'Scan QR to Borrow' : 'Scan QR to Return';
    setScannerState(null, 'Scanning…');

    html5QrCode = new Html5Qrcode("qr-reader");
    html5QrCode.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: 280 },
      (decodedText) => {
        if (scanLocked) return;   // ignore extra frames while we're mid-animation
        scanLocked = true;
        setScannerState('success', 'QR Detected ✔');
        setTimeout(() => {
          stopScanner();
          // decodedText is the qr_code string (e.g. "HAMMER001") stuck on the tool.
          // Backend resolves this to the real tool_id — logic unchanged.
          handleScanResult(decodedText.trim());
        }, 600);
      },
      () => { /* ignore per-frame decode misses */ }
    ).catch(err => {
      setScannerState('error', 'Could not start camera');
      showMessage('Could not start camera: ' + err, true);
      wrap.style.display = 'none';
    });
  }

 function handleScanResult(scannedValue) {
    const url = scanMode === 'borrow' ? '/api/borrow' : '/api/return';
    const qty = scanMode === 'borrow'
      ? (parseInt(document.getElementById('borrow-qty-input')?.value, 10) || 1)
      : 1;
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool_id: scannedValue, quantity: qty })
    })
      .then(r => r.json())
      .then(data => {
        showMessage(data.message, !data.success);
        if (data.success) loadToolDropdowns();
      });
  }

  const btnScanBorrow = document.getElementById('btn-scan-borrow');
  if (btnScanBorrow) btnScanBorrow.addEventListener('click', () => startScanner('borrow'));

  const btnScanReturn = document.getElementById('btn-scan-return');
  if (btnScanReturn) btnScanReturn.addEventListener('click', () => startScanner('return'));

  const btnStopScan = document.getElementById('btn-stop-scan');
  if (btnStopScan) btnStopScan.addEventListener('click', stopScanner);

  // ---------- LOAD WHATEVER THIS PAGE NEEDS ----------
  if (document.getElementById('stat-total-borrowed')) loadStats();
  if (document.getElementById('borrow-tool-select') || document.getElementById('return-tool-select')) loadToolDropdowns();
  if (document.getElementById('mytools-body')) loadMyTools();
  if (document.getElementById('history-body')) loadHistory();

});