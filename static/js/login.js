const resultDiv  = document.getElementById('result');
const scanStatus = document.getElementById('scanStatus');
const scannerFrame = document.getElementById('scanner-frame');

function showResult(html, type) {
  resultDiv.innerHTML = html;
  resultDiv.className = `result ${type}`;
}

function setScannerState(state, text) {
  if (scannerFrame) scannerFrame.classList.remove('success', 'error');
  if (scanStatus)   scanStatus.classList.remove('success', 'error');
  if (state && scannerFrame) scannerFrame.classList.add(state);
  if (state && scanStatus)   scanStatus.classList.add(state);
  if (scanStatus && text) scanStatus.textContent = text;
}

async function verifyLogin(employee_id) {
  try {
    const res    = await fetch('/api/login', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ employee_id }),
    });
    const result = await res.json();

    if (result.success) {
      setScannerState('success', '✅ Login verified');
      showResult(`✅ ${result.message}<br><small>Redirecting...</small>`, 'success');
      setTimeout(() => { window.location.href = result.redirect || '/dashboard'; }, 1000);
    } else {
      setScannerState('error', '✗ Login failed');
      showResult(`✗ ${result.message}`, 'error');
    }
  } catch (err) {
    setScannerState('error', 'Server error');
    showResult('Server error. Please try again.', 'error');
    console.error(err);
  }
}

let qrScannerRunning = true;

function onScanSuccess(decodedText) {
  if (!qrScannerRunning) return;
  qrScannerRunning = false;

  console.log('QR Decoded:', decodedText);
  setScannerState('success', '✅ QR Code detected!');

  let employee_id = decodedText.trim();
  try {
    const parsed = JSON.parse(decodedText);
    employee_id  = parsed.employee_id || parsed.id || employee_id;
  } catch (e) {}

  showResult(`QR found: <strong>${employee_id}</strong> — verifying...`, 'info');
  verifyLogin(employee_id.toUpperCase());

  html5QrCode.stop().catch(err => console.log(err));
}

function onScanFailure(error) {}

const html5QrCode = new Html5Qrcode("reader");

html5QrCode.start(
  { facingMode: "environment" },
  { fps: 10, qrbox: { width: 280, height: 280 } },
  onScanSuccess,
  onScanFailure
).then(() => {
  setScannerState(null, 'Point QR code on ID card at camera');
}).catch(err => {
  console.error('Camera start error:', err);
  setScannerState('error', 'Camera unavailable — use manual entry below');
  showResult('Camera access denied. Please use manual entry.', 'error');
});

document.getElementById('manualBtn').addEventListener('click', async () => {
  const employee_id = document.getElementById('manualId').value.trim().toUpperCase();
  if (!employee_id) {
    showResult('Please enter an Employee ID.', 'error');
    return;
  }
  showResult(`Verifying ${employee_id}...`, 'info');
  await verifyLogin(employee_id);
});

document.getElementById('manualId').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    document.getElementById('manualBtn').click();
  }
});
// ===== TAB SWITCHING =====
function switchTab(tab) {
  document.getElementById('employeeTabBtn').classList.toggle('active', tab === 'employee');
  document.getElementById('adminTabBtn').classList.toggle('active', tab === 'admin');
  document.getElementById('employeeTab').classList.toggle('active', tab === 'employee');
  document.getElementById('adminTab').classList.toggle('active', tab === 'admin');
}

// ===== ADMIN LOGIN =====
const adminResultDiv = document.getElementById('adminResult');

function showAdminResult(html, type) {
  adminResultDiv.innerHTML = html;
  adminResultDiv.className = `result ${type}`;
}

document.getElementById('adminLoginBtn').addEventListener('click', async () => {
  const username = document.getElementById('adminUsername').value.trim();
  const password = document.getElementById('adminPassword').value;

  if (!username || !password) {
    showAdminResult('Please enter username and password.', 'error');
    return;
  }

  try {
    const res = await fetch('/api/admin-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const result = await res.json();

    if (result.success) {
      showAdminResult(`✅ ${result.message}`, 'success');
      setTimeout(() => { window.location.href = result.redirect; }, 800);
    } else {
      showAdminResult(`✗ ${result.message}`, 'error');
    }
  } catch (err) {
    showAdminResult('Server error. Please try again.', 'error');
  }
});
function showForgotInfo() {
  showAdminResult(
    '🔒 Please contact the Super Admin / IT department to reset your password.',
    'info'
  );
}