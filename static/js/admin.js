document.addEventListener('DOMContentLoaded', () => {

  // ---------- HELPERS ----------
  function dash(v) { return (v !== null && v !== undefined && v !== 'None' && v !== '') ? v : '—'; }

  function badge(status) {
    const cls = (status || '').toLowerCase();
    return `<span class="badge ${cls}">${status || '—'}</span>`;
  }

  function showMessage(elId, text, isError) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = text;
    el.className = 'message ' + (isError ? 'error' : 'success');
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 4000);
  }

  async function api(url, options = {}) {
    const res = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
    return res.json();
  }

  // ---------- DASHBOARD ----------
  async function loadSummary() {
    const data = await api('/api/admin/summary');
    if (!data.success) return;
    document.getElementById('stat-total-employees').textContent = data.stats.total_employees;
    document.getElementById('stat-total-tools').textContent     = data.stats.total_tools;
    document.getElementById('stat-borrowed').textContent        = data.stats.borrowed;
    document.getElementById('stat-returned').textContent        = data.stats.returned;
    document.getElementById('stat-overdue').textContent         = data.stats.overdue;

    const txns = await api('/api/admin/transactions');
    const tbody = document.getElementById('dash-recent-body');
    if (!tbody) return;
    if (txns.success && txns.transactions.length) {
      tbody.innerHTML = txns.transactions.slice(0, 6).map(t => `
        <tr>
          <td>${t.employee_name} (${t.employee_id})</td>
          <td>${t.tool_name}</td>
          <td>${dash(t.borrow_date)}</td>
          <td>${dash(t.due_date)}</td>
          <td>${badge(t.status)}</td>
        </tr>`).join('');
    } else {
      tbody.innerHTML = `<tr><td colspan="5" class="empty-row">No transactions yet.</td></tr>`;
    }
  }

  // ---------- EMPLOYEES ----------
  async function loadEmployees() {
    const tbody = document.getElementById('employees-body');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="3" class="empty-row">Loading…</td></tr>`;
    const data = await api('/api/admin/employees');
    if (data.success && data.employees.length) {
      tbody.innerHTML = data.employees.map(e => `
        <tr><td>${e.employee_id}</td><td>${e.name}</td><td>${dash(e.contact_no)}</td></tr>
      `).join('');
    } else {
      tbody.innerHTML = `<tr><td colspan="3" class="empty-row">No employees found.</td></tr>`;
    }
  }

  // ---------- TOOLS ----------
  async function loadTools() {
    const tbody = document.getElementById('tools-body');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="5" class="empty-row">Loading…</td></tr>`;
    const data = await api('/api/admin/tools');
    if (data.success && data.tools.length) {
      tbody.innerHTML = data.tools.map(t => `
        <tr>
          <td>${t.tool_id}</td>
          <td>${t.tool_name}</td>
          <td>${dash(t.category)}</td>
          <td>${badge(t.status)}</td>
          <td><button class="btn btn-danger btn-sm" data-delete-tool="${t.tool_id}">Delete</button></td>
        </tr>`).join('');
    } else {
      tbody.innerHTML = `<tr><td colspan="5" class="empty-row">No tools yet — add one above.</td></tr>`;
    }
  }

  const btnAddTool = document.getElementById('btn-add-tool');
  if (btnAddTool) {
    btnAddTool.addEventListener('click', async () => {
      const tool_name = document.getElementById('tool-name-input').value.trim();
      const category  = document.getElementById('tool-category-input').value.trim();
      const total_qty = document.getElementById('tool-qty-input').value.trim() || 1;

      if (!tool_name) return showMessage('tool-message', 'Tool name is required.', true);

      const res = await api('/api/admin/tools', {
        method: 'POST',
        body: JSON.stringify({ tool_name, category, total_qty })
      });

      if (res.success) {
        showMessage('tool-message', 'Tool added.', false);
        document.getElementById('tool-name-input').value = '';
        document.getElementById('tool-category-input').value = '';
        document.getElementById('tool-qty-input').value = '';
        loadTools();
      } else {
        showMessage('tool-message', res.message || 'Could not add tool.', true);
      }
    });
  }

  const toolsBody = document.getElementById('tools-body');
  if (toolsBody) {
    toolsBody.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-delete-tool]');
      if (!btn) return;
      const toolId = btn.getAttribute('data-delete-tool');
      if (!confirm('Delete this tool? This cannot be undone.')) return;
      const res = await api(`/api/admin/tools/${toolId}`, { method: 'DELETE' });
      showMessage('tool-message', res.success ? 'Tool deleted.' : (res.message || 'Could not delete tool.'), !res.success);
      loadTools();
    });
  }

  // ---------- TRANSACTIONS ----------
  async function loadTransactions() {
    const tbody = document.getElementById('transactions-body');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="8" class="empty-row">Loading…</td></tr>`;

    const status = document.getElementById('filter-status')?.value || '';
    const range  = document.getElementById('filter-range')?.value || '';

    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (range) params.set('range', range);

    const data = await api('/api/admin/transactions?' + params.toString());
    if (data.success && data.transactions.length) {
      tbody.innerHTML = data.transactions.map(t => `
        <tr>
          <td>${t.employee_name} (${t.employee_id})</td>
          <td>${t.tool_name}</td>
          <td>${dash(t.borrow_date)}</td>
          <td>${dash(t.borrow_time)}</td>
          <td>${dash(t.due_date)}</td>
          <td>${dash(t.return_date)}</td>
          <td>${dash(t.return_time)}</td>
          <td>${badge(t.status)}</td>
        </tr>`).join('');
    } else {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-row">No matching transactions.</td></tr>`;
    }
  }

  const btnApplyFilter = document.getElementById('btn-apply-filter');
  if (btnApplyFilter) btnApplyFilter.addEventListener('click', loadTransactions);

  // ---------- REPORTS / EXPORT ----------
  const btnExportCsv = document.getElementById('btn-export-csv');
  if (btnExportCsv) {
    btnExportCsv.addEventListener('click', async () => {
      const data = await api('/api/admin/transactions');
      if (!data.success || !data.transactions.length) {
        return showMessage('report-message', 'No transactions to export.', true);
      }
      const header = ['Employee ID', 'Employee', 'Tool', 'Borrow Date', 'Borrow Time', 'Return Date', 'Return Time', 'Due Date', 'Status'];
      const lines = [header.join(',')];
      data.transactions.forEach(t => {
        lines.push([t.employee_id, t.employee_name, t.tool_name, t.borrow_date, t.borrow_time, t.return_date || '', t.return_time || '', t.due_date || '', t.status]
          .map(v => `"${v ?? ''}"`).join(','));
      });
      const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'transactions.csv';
      a.click();
      showMessage('report-message', 'CSV downloaded.', false);
    });
  }

  const btnExportPdf = document.getElementById('btn-export-pdf');
  if (btnExportPdf) btnExportPdf.addEventListener('click', () => window.print());

  // ---------- LOAD WHATEVER THIS PAGE NEEDS ----------
  if (document.getElementById('stat-total-employees')) loadSummary();
  if (document.getElementById('employees-body')) loadEmployees();
  if (document.getElementById('tools-body')) loadTools();
  if (document.getElementById('transactions-body')) loadTransactions();

});