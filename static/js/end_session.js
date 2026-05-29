/** End session and download current interview PDF report */
async function endSessionAndDownload() {
    try {
        const resp = await fetch('/api/download_session_pdf');
        if (!resp.ok) {
            let msg = 'Download failed';
            try {
                const data = await resp.json();
                msg = data.error || msg;
            } catch (_) {}
            alert(msg);
            return;
        }
        const blob = await resp.blob();
        const cd = resp.headers.get('Content-Disposition') || '';
        let filename = 'interview_report.pdf';
        const match = cd.match(/filename="?([^";]+)"?/i);
        if (match) filename = match[1];

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    } catch (err) {
        alert('Download failed: ' + err.message);
    }
}
