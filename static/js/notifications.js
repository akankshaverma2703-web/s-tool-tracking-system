document.addEventListener('DOMContentLoaded', () => {
  const bell = document.getElementById('notif-bell');
  if (!bell) return;

  const isAdmin = bell.dataset.role === 'admin';
  const listUrl = isAdmin ? '/api/admin/notifications' : '/api/notifications';
  const readAllUrl = isAdmin ? '/api/admin/notifications/mark-all-read' : '/api/notifications/mark-all-read';

  const badge = document.getElementById('notif-badge');
  const panel = document.getElementById('notif-panel');
  const list  = document.getElementById('notif-list');

  function timeAgo(dateStr) {
    const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
  }

  function iconFor(type) {
    return { borrow: '📦', return: '✅', due_soon: '⏰', overdue: '⚠️', low_stock: '📉' }[type] || '🔔';
  }

  function loadNotifications() {
    fetch(listUrl)
      .then(r => r.json())
      .then(data => {
        if (!data.success) return;
        badge.textContent = data.unread_count;
        badge.style.display = data.unread_count > 0 ? 'flex' : 'none';

        if (!data.notifications.length) {
          list.innerHTML = '<div class="notif-empty">No notifications yet.</div>';
          return;
        }
        list.innerHTML = data.notifications.map(n => `
          <div class="notif-item ${n.status === 'unread' ? 'unread' : ''}">
            <span class="notif-ic">${iconFor(n.type)}</span>
            <div class="notif-body">
              <div class="notif-msg">${n.message}</div>
              <div class="notif-time">${timeAgo(n.created_at)}</div>
            </div>
          </div>
        `).join('');
      })
      .catch(() => {});
  }

  bell.addEventListener('click', () => {
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) loadNotifications();
  });

  document.addEventListener('click', (e) => {
    if (!panel.contains(e.target) && !bell.contains(e.target)) {
      panel.classList.remove('open');
    }
  });

  const markAllBtn = document.getElementById('notif-mark-all');
  if (markAllBtn) {
    markAllBtn.addEventListener('click', () => {
      fetch(readAllUrl, { method: 'POST' }).then(() => loadNotifications());
    });
  }

  loadNotifications();
  setInterval(loadNotifications, 30000); // poll every 30s
});
