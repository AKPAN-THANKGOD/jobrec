document.querySelectorAll('#hist [data-del]').forEach(btn => {
  btn.onclick = () => {
    const id = btn.closest('li').dataset.id;
    del(id);
  };
});

async function del(id){
  if (!confirm('Delete this entry?')) return;
  try {
    const r = await fetch('/profile/history/' + encodeURIComponent(id), {method:'DELETE'});
    if (!r.ok) return alert('Delete failed');
    location.reload();
  } catch {
    alert('Network error');
  }
}