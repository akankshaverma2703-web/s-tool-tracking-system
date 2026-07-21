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
  let chartBorrowTrend, chartStatusDist, chartTopTools, chartReturnTrend, chartMonthlyTxns;

  function destroyChart(chart) {
    if (chart) chart.destroy();
  }

  function renderBorrowTrendChart(transactions) {
    const canvas = document.getElementById('chart-borrow-trend');
    if (!canvas || typeof Chart === 'undefined') return;

    const days = [];
    const counts = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      days.push(key.slice(5));
      counts.push(transactions.filter(t => t.borrow_date === key).length);
    }

    destroyChart(chartBorrowTrend);
    chartBorrowTrend = new Chart(canvas, {
      type: 'line',
      data: {
        labels: days,
        datasets: [{
          label: 'Tools Borrowed',
          data: counts,
          borderColor: '#3d5afe',
          backgroundColor: 'rgba(61,90,254,0.12)',
          tension: 0.35,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: '#3d5afe'
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
  }

  function renderReturnTrendChart(transactions) {
    const canvas = document.getElementById('chart-return-trend');
    if (!canvas || typeof Chart === 'undefined') return;

    const days = [];
    const counts = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      days.push(key.slice(5));
      counts.push(transactions.filter(t => t.return_date === key).length);
    }

    destroyChart(chartReturnTrend);
    chartReturnTrend = new Chart(canvas, {
      type: 'line',
      data: {
        labels: days,
        datasets: [{
          label: 'Tools Returned',
          data: counts,
          borderColor: '#16a34a',
          backgroundColor: 'rgba(22,163,74,0.12)',
          tension: 0.35,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: '#16a34a'
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
  }

  function renderStatusDistChart(stats) {
    const canvas = document.getElementById('chart-status-dist');
    if (!canvas || typeof Chart === 'undefined' || !stats) return;

    destroyChart(chartStatusDist);
    chartStatusDist = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Active', 'Returned', 'Overdue'],
        datasets: [{
          data: [stats.borrowed, stats.returned, stats.overdue],
          backgroundColor: ['#3d5afe', '#16a34a', '#dc2626'],
          borderWidth: 0
        }]
      },
      options: {
        plugins: { legend: { position: 'bottom' } },
        cutout: '65%'
      }
    });
  }

  function renderMonthlyTxnsChart(transactions) {
    const canvas = document.getElementById('chart-monthly-txns');
    if (!canvas || typeof Chart === 'undefined') return;

    const months = [];
    const labels = [];
    for (let i = 5; i >= 0; i--) {
      const d = new Date();
      d.setMonth(d.getMonth() - i);
      const key = d.toISOString().slice(0, 7); // YYYY-MM
      months.push(key);
      labels.push(d.toLocaleString('default', { month: 'short', year: '2-digit' }));
    }
    const counts = months.map(m => transactions.filter(t => (t.borrow_date || '').startsWith(m)).length);

    destroyChart(chartMonthlyTxns);
    chartMonthlyTxns = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Transactions',
          data: counts,
          backgroundColor: '#3d5afe',
          borderRadius: 6,
          maxBarThickness: 46
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
  }

  function renderTopToolsChart(transactions) {
    const canvas = document.getElementById('chart-top-tools');
    if (!canvas || typeof Chart === 'undefined') return;

    const counts = {};
    transactions.forEach(t => { counts[t.tool_name] = (counts[t.tool_name] || 0) + 1; });
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 6);

    destroyChart(chartTopTools);
    chartTopTools = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: sorted.map(s => s[0]),
        datasets: [{
          label: 'Times Borrowed',
          data: sorted.map(s => s[1]),
          backgroundColor: '#5470ff',
          borderRadius: 6,
          maxBarThickness: 40
        }]
      },
      options: {
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
  }

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

    if (txns.success && txns.transactions.length) {
      renderBorrowTrendChart(txns.transactions);
      renderReturnTrendChart(txns.transactions);
      renderMonthlyTxnsChart(txns.transactions);
      renderTopToolsChart(txns.transactions);
    }
    renderStatusDistChart(data.stats);

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
    tbody.innerHTML = `<tr><td colspan="6" class="empty-row">Loading…</td></tr>`;
    const data = await api('/api/admin/employees');
    if (data.success && data.employees.length) {
      tbody.innerHTML = data.employees.map(e => `
        <tr>
          <td>${e.employee_id}</td>
          <td>${e.name}</td>
          <td>${dash(e.company_name)}</td>
          <td>${dash(e.contact_no)}</td>
          <td>${dash(e.email)}</td>
          <td><a class="btn btn-outline btn-sm" href="/api/admin/employees/${e.employee_id}/qr" target="_blank">View / Print QR</a></td>
        </tr>
      `).join('');
    } else {
      tbody.innerHTML = `<tr><td colspan="6" class="empty-row">No employees found.</td></tr>`;
    }
  }

  const btnAddEmployee = document.getElementById('btn-add-employee');
  if (btnAddEmployee) {
    btnAddEmployee.addEventListener('click', async () => {
      const employee_id  = document.getElementById('employee-id-input').value.trim();
      const name          = document.getElementById('employee-name-input').value.trim();
      const company_name  = document.getElementById('employee-company_name-input')?.value.trim() || '';
      const contact_no    = document.getElementById('employee-contact-input')?.value.trim() || '';
      const email         = document.getElementById('employee-email-input')?.value.trim() || '';

      if (!employee_id) return showMessage('employee-message', 'Employee ID is required.', true);
      if (!name)         return showMessage('employee-message', 'Name is required.', true);

      const res = await api('/api/admin/employees', {
        method: 'POST',
        body: JSON.stringify({ employee_id, name, company_name, contact_no, email })
      });

      if (res.success) {
        showMessage('employee-message', res.message || 'Employee added.', false);
        document.getElementById('employee-id-input').value = '';
        document.getElementById('employee-name-input').value = '';
        if (document.getElementById('employee-company_name-input')) document.getElementById('employee-company_name-input').value = '';
        if (document.getElementById('employee-contact-input')) document.getElementById('employee-contact-input').value = '';
        if (document.getElementById('employee-email-input')) document.getElementById('employee-email-input').value = '';

        const qrWrap = document.getElementById('new-emp-qr-wrap');
        if (qrWrap) {
          const qrUrl = `/api/admin/employees/${encodeURIComponent(employee_id)}/qr`;
          document.getElementById('new-emp-qr-img').src = qrUrl;
          document.getElementById('new-emp-qr-download').href = qrUrl;
          document.getElementById('new-emp-qr-download').setAttribute('download', `${employee_id}_qr.png`);
          qrWrap.style.display = 'block';
        }

        loadEmployees();
      } else {
        showMessage('employee-message', res.message || 'Could not add employee.', true);
      }
    });
  }

  // ---------- TOOLS ----------
  async function loadTools() {
    const tbody = document.getElementById('tools-body');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="6" class="empty-row">Loading…</td></tr>`;
    const data = await api('/api/admin/tools');
    if (data.success && data.tools.length) {
      tbody.innerHTML = data.tools.map(t => `
        <tr>
          <td>${t.tool_id}</td>
          <td>${t.tool_name}</td>
          <td>${dash(t.category)}</td>
          <td>${badge(t.status)}</td>
          <td>
            <code>${dash(t.qr_code)}</code>
            <a class="btn btn-outline btn-sm" href="/api/admin/tools/${t.tool_id}/qr" target="_blank" style="margin-left:6px;">View / Print</a>
          </td>
          <td><button class="btn btn-danger btn-sm" data-delete-tool="${t.tool_id}">Delete</button></td>
        </tr>`).join('');
    } else {
      tbody.innerHTML = `<tr><td colspan="6" class="empty-row">No tools yet — add one above.</td></tr>`;
    }
  }

  const btnAddTool = document.getElementById('btn-add-tool');
  if (btnAddTool) {
    btnAddTool.addEventListener('click', async () => {
      const tool_name = document.getElementById('tool-name-input').value.trim();
      const category  = document.getElementById('tool-category-input').value.trim();
      const total_qty = document.getElementById('tool-qty-input').value.trim() || 1;
      const qr_code   = document.getElementById('tool-qrcode-input')?.value.trim() || '';

      if (!tool_name) return showMessage('tool-message', 'Tool name is required.', true);

      const res = await api('/api/admin/tools', {
        method: 'POST',
        body: JSON.stringify({ tool_name, category, total_qty, qr_code })
      });

      if (res.success) {
        showMessage('tool-message', 'Tool added.', false);
        document.getElementById('tool-name-input').value = '';
        document.getElementById('tool-category-input').value = '';
        document.getElementById('tool-qty-input').value = '';
        if (document.getElementById('tool-qrcode-input')) document.getElementById('tool-qrcode-input').value = '';
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
    tbody.innerHTML = `<tr><td colspan="9" class="empty-row">Loading…</td></tr>`;

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
          <td>${dash(t.company_name)}</td>
          <td>${t.tool_name}</td>
          <td>${dash(t.borrow_date)}</td>
          <td>${dash(t.borrow_time)}</td>
          <td>${dash(t.due_date)}</td>
          <td>${dash(t.return_date)}</td>
          <td>${dash(t.return_time)}</td>
          <td>${badge(t.status)}</td>
        </tr>`).join('');
    } else {
      tbody.innerHTML = `<tr><td colspan="9" class="empty-row">No matching transactions.</td></tr>`;
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