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
      if (!toolId) return;
      fetch('/api/borrow', {
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

  // ---------- MY TOOLS TABLE ----------
  function loadMyTools() {
    fetch('/api/my-tools')
      .then(r => r.json())
      .then(data => {
        const body = document.getElementById('mytools-body');
        if (!body) return;
        if (!data.tools || data.tools.length === 0) {
          body.innerHTML = '<tr><td colspan="5" class="empty-row">No tools currently borrowed.</td></tr>';
          return;
        }
        body.innerHTML = data.tools.map(t => `
          <tr>
            <td>${t.tool_name}</td>
            <td>${t.borrow_date}</td>
            <td>${t.borrow_time}</td>
            <td>${t.due_date}</td>
            <td>${statusBadge(t.status)}</td>
          </tr>
        `).join('');
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

  // ---------- LOAD WHATEVER THIS PAGE NEEDS ----------
  if (document.getElementById('stat-total-borrowed')) loadStats();
  if (document.getElementById('borrow-tool-select') || document.getElementById('return-tool-select')) loadToolDropdowns();
  if (document.getElementById('mytools-body')) loadMyTools();
  if (document.getElementById('history-body')) loadHistory();

});