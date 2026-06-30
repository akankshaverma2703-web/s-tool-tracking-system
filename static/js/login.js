const resultDiv  = document.getElementById('result');
const scanStatus = document.getElementById('scanStatus');

function showResult(html, type) {
  resultDiv.innerHTML = html;
  resultDiv.className = `result ${type}`;
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
      showResult(`✅ ${result.message}<br><small>Redirecting...</small>`, 'success');
      setTimeout(() => { window.location.href = '/'; }, 1000);
    } else {
      showResult(`✗ ${result.message}`, 'error');
    }
  } catch (err) {
    showResult('Server error. Please try again.', 'error');
    console.error(err);
  }
}

let qrScannerRunning = true;

function onScanSuccess(decodedText) {
  if (!qrScannerRunning) return;
  qrScannerRunning = false;

  console.log('QR Decoded:', decodedText);
  scanStatus.textContent = '✅ QR Code detected!';

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
  { fps: 10, qrbox: { width: 220, height: 220 } },
  onScanSuccess,
  onScanFailure
).then(() => {
  scanStatus.textContent = 'Point QR code on ID card at camera';
}).catch(err => {
  console.error('Camera start error:', err);
  scanStatus.textContent = 'Camera unavailable — use manual entry below';
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