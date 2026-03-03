(function() {
  var API = (function() {
    var h = window.location.hostname;
    var local = h === 'localhost' || h === '127.0.0.1';
    var priv = h.startsWith('192.168.') || h.startsWith('10.') || h.startsWith('172.');
    if (local || priv) return 'http://' + h + ':8000';
    return window.location.origin;
  })();
  fetch(API + '/api/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: window.location.pathname })
  }).catch(function() {});
})();
