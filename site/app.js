// Small checker for the "lowest price in the last 30 days" rule.
// Same logic as src/omnibus.py, kept in step by the tests.
(function () {
  function toDay(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s).trim());
    if (!m) throw new Error("Please write dates like 2026-11-13.");
    return Date.UTC(+m[1], +m[2] - 1, +m[3]) / 86400000;
  }
  function parseHistory(text) {
    var rows = [];
    text.trim().split(/\r?\n/).forEach(function (line) {
      line = line.trim();
      if (!line || /^date/i.test(line)) return;
      var parts = line.replace(/;/g, ",").split(",");
      var price = parseFloat(String(parts[1]).replace("€", "").replace(",", "."));
      if (isNaN(price)) throw new Error("Could not read the price on this line: " + line);
      rows.push([toDay(parts[0]), price]);
    });
    rows.sort(function (a, b) { return a[0] - b[0]; });
    return rows;
  }
  function priceOn(history, day) {
    var current = null;
    for (var i = 0; i < history.length; i++) {
      if (history[i][0] <= day) current = history[i][1]; else break;
    }
    return current;
  }
  function lowestBefore(history, start) {
    var low = null;
    for (var day = start - 30; day < start; day++) {
      var p = priceOn(history, day);
      if (p !== null && (low === null || p < low)) low = p;
    }
    return low;
  }
  function check(history, start, regular, sale) {
    var low = lowestBefore(history, start);
    if (low === null) return { ok: false, text: "There is no price in the 30 days before the reduction, so there is nothing to compare with." };
    var shown = Math.round((1 - sale / regular) * 100);
    var real = Math.round((1 - sale / low) * 100);
    if (Math.abs(regular - low) < 0.005) return { ok: true, low: low, text: "The “before” price matches the lowest price of the last 30 days." };
    if (regular > low) return { ok: false, low: low, text: "The “before” price (" + regular.toFixed(2) + ") is higher than the lowest price in the 30 days before (" + low.toFixed(2) + "). The real reduction is " + real + "%, not " + shown + "%." };
    return { ok: true, low: low, text: "The “before” price is lower than the 30-day low, so the claim is on the safe side." };
  }
  window.priceCheck = { parseHistory: parseHistory, check: check, toDay: toDay };

  var form = document.getElementById("checker");
  if (!form) return;
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var out = document.getElementById("result");
    try {
      var r = check(
        parseHistory(document.getElementById("hist").value),
        toDay(document.getElementById("start").value),
        parseFloat(document.getElementById("regular").value.replace(",", ".")),
        parseFloat(document.getElementById("sale").value.replace(",", "."))
      );
      out.className = r.ok ? "" : "bad";
      out.textContent = r.text + (r.low != null ? " Line to show: “Lowest price in the last 30 days: €" + r.low.toFixed(2) + "”." : "");
    } catch (err) {
      out.className = "bad";
      out.textContent = err.message;
    }
  });
})();
