(async () => {
  // 1) Try to find the XLSX link in the "Broker Protocol Member Firms" section
  const sectionHeading = Array.from(document.querySelectorAll('h3'))
    .find(h => h.textContent.trim().toLowerCase() === 'broker protocol member firms');

  let linkEl = null;

  if (sectionHeading) {
    const sectionRoot = sectionHeading.closest('[data-column-content]') || sectionHeading.parentElement;
    linkEl = sectionRoot?.querySelector('a[href$=".xlsx"]') || null;
  }

  // 2) Fallback: find any XLSX that looks like the member firms list
  if (!linkEl) {
    linkEl = document.querySelector('a[href$=".xlsx"][href*="The-Broker-Protocol-Member-Firms"]')
      || document.querySelector('a[href*="Broker-Protocol"][href$=".xlsx"]')
      || Array.from(document.querySelectorAll('a[href$=".xlsx"]'))
          .find(a => /broker|protocol|member|firms/i.test(a.getAttribute('href') || ''))
      || null;
  }

  if (!linkEl) {
    console.error("Couldn't find the XLSX link on this page.");
    return;
  }

  const url = new URL(linkEl.getAttribute('href'), window.location.href).href;
  const filename = decodeURIComponent(url.split('/').pop().split('?')[0] || 'broker-protocol-member-firms.xlsx');

  console.log('Found XLSX:', url);
  console.log('Downloading as:', filename);

  // 3) Download (Blob) so the browser saves it as a file
  const resp = await fetch(url, { credentials: 'include' });
  if (!resp.ok) throw new Error(`Download failed: ${resp.status} ${resp.statusText}`);

  const blob = await resp.blob();
  const blobUrl = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();

  // cleanup
  setTimeout(() => URL.revokeObjectURL(blobUrl), 10_000);

  console.log('Done.');
})().catch(err => console.error(err));
