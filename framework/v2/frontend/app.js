const MATCHERS = ["structure", "linguistic", "content", "terminology"];
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

// ---------- cascade order (drag and drop)
const order = $("#order");
MATCHERS.forEach(m => {
  const li = document.createElement("li");
  li.draggable = true; li.dataset.m = m;
  li.innerHTML = `<input type="checkbox" checked> ${m}`;
  order.appendChild(li);
});
let dragged = null;
order.addEventListener("dragstart", e => { dragged = e.target.closest("li"); });
order.addEventListener("dragover", e => {
  e.preventDefault();
  const over = e.target.closest("li");
  if (over && over !== dragged) {
    const r = over.getBoundingClientRect();
    order.insertBefore(dragged, e.clientY > r.top + r.height / 2 ? over.nextSibling : over);
  }
});

// ---------- oracle inputs
document.querySelectorAll(".oracle").forEach(div => {
  const p = div.dataset.pattern.toUpperCase();
  div.innerHTML = `<select><option value="">${p}: extract</option><option value="triple">${p}: triple</option>
    <option value="single_term">${p}: single term</option><option value="sequence_of_words">${p}: sequence of words</option></select>
    <div class="fields"></div>`;
  const sel = $("select", div), fields = $(".fields", div);
  sel.onchange = () => {
    fields.innerHTML = sel.value === "triple"
      ? `<input data-k="subject" placeholder="subject"><input data-k="predicate" placeholder="predicate"><input data-k="object" placeholder="object">`
      : sel.value ? `<input data-k="text" placeholder="text" style="grid-column:span 3">` : "";
  };
});

function oracleOf(ideaEl, pattern) {
  const div = ideaEl.querySelector(`.oracle[data-pattern=${pattern}]`);
  const type = $("select", div).value;
  if (!type) return null;
  const o = { type };
  div.querySelectorAll("input").forEach(i => o[i.dataset.k] = i.value.trim());
  return o;
}

function ideaOf(n) {
  const el = $(`#idea${n}`);
  return { what: $("[name=what]", el).value, how: $("[name=how]", el).value, when: $("[name=when]", el).value,
           oracle_what: oracleOf(el, "what"), oracle_how: oracleOf(el, "how") };
}

function options() {
  const items = [...order.querySelectorAll("li")];
  return {
    extractor: $("#extractor").value,
    order: items.map(li => li.dataset.m),
    enabled: items.filter(li => $("input", li).checked).map(li => li.dataset.m),
    linguistic: +$("#linguistic").value, content: +$("#content").value, terminology: +$("#terminology").value,
    implicit_how_subject: $("#implicit").checked, sd_vd_od: $("#sdvdod").value,
    rules_version: $("#rulesv").value, abstain: $("#abstain").checked, segmenter: "syntax",
  };
}

// ---------- rendering
function element(e) {
  if (e.type === "triple") return `&lt;${esc(e.subject)} | ${esc(e.predicate)} | ${esc(e.object)}&gt;`;
  if (e.type === "empty") return "<i>empty</i>";
  return `“${esc(e.text)}”`;
}

function render(d) {
  $("#result").hidden = false;
  const v = $(".verdict"); v.className = "verdict r-" + d.relationship;
  $("#rel").textContent = d.relationship;
  $("#direction").textContent = d.direction || "";
  const how = d.how_rule_id.startsWith("HOW-") ? `HOW ${d.how_rule_id.slice(4).toLowerCase()}`
    : d.how_rule_id === "-" ? "" : `HOW ${d.how_same ? "same" : "different"} (rule ${d.how_rule_id})`;
  $("#rule").textContent = [d.rule_text, how].filter(Boolean).join(" · ");
  $("#elements").innerHTML = ["idea1", "idea2"].flatMap(k => ["WHAT", "HOW"].map(p => {
    const e = d.elements[k][p];
    return `<div class="card"><b>${k === "idea1" ? "Idea 1" : "Idea 2"} · ${p} <span class="tag">${esc(e.type.replaceAll("_", " "))}</span><span class="tag">${esc(e.source)}</span></b>${element(e)}</div>`;
  })).join("");
  $("#links").innerHTML = d.links.length ? d.links.map(l => `
    <div class="link"><span class="${l.link === "no_link" ? "no" : "ok"}">${esc(l.term1)} ~ ${esc(l.term2)} → ${esc(l.link)}</span>
      ${l.matcher ? `<span class="tag">${esc(l.matcher)}</span>` : ""}
      <div class="calls">${l.calls.map(c => `${esc(c.matcher)}: ${esc(c.link)}${c.score != null ? ` (score ${c.score}${c.threshold != null ? ` / thr ${c.threshold}` : ""})` : ""} – ${esc(c.detail)}`).join("<br>")}</div>
    </div>`).join("") : "<p class='hint'>No term comparison was needed.</p>";
  $("#codes").innerHTML = Object.entries(d.codes).map(([k, v]) => `<span>${esc(k)} = <b>${esc(v)}</b></span>`).join("")
    + d.notes.map(n => `<p class="hint">${esc(n)}</p>`).join("");
  $("#json").textContent = JSON.stringify(d, null, 2);
  $("#result").scrollIntoView({ behavior: "smooth" });
}

$("#run").onclick = async () => {
  const btn = $("#run"); btn.disabled = true; $("#status").textContent = "running (the first call loads the language resources)…";
  try {
    const r = await fetch("/api/compare", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea1: ideaOf(1), idea2: ideaOf(2), options: options() }) });
    const d = await r.json();
    if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail));
    render(d); $("#status").textContent = "";
  } catch (e) { $("#status").textContent = "Error: " + e.message; }
  btn.disabled = false;
};

// ---------- Step 1: free text -> patterns
document.querySelectorAll(".split").forEach(btn => btn.onclick = async () => {
  const el = $(`#idea${btn.dataset.target}`);
  const text = $("[name=free]", el).value.trim(); if (!text) return;
  const r = await fetch("/api/segment", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, options: options() }) });
  const d = await r.json();
  $("[name=what]", el).value = d.what || ""; $("[name=how]", el).value = d.how || ""; $("[name=when]", el).value = d.when || "";
});

// ---------- examples and rules
fetch("/api/examples").then(r => r.json()).then(list => {
  document.querySelectorAll(".example").forEach(sel => {
    list.forEach(i => sel.insertAdjacentHTML("beforeend", `<option value="${esc(i.id)}">${esc(i.id)}: ${esc((i.what || i.text).slice(0, 50))}</option>`));
    sel.onchange = () => {
      const i = list.find(x => x.id === sel.value); if (!i) return;
      const el = $(`#idea${sel.dataset.target}`);
      $("[name=what]", el).value = i.what; $("[name=how]", el).value = i.how; $("[name=when]", el).value = i.when;
    };
  });
});
// paper example as starting point
$("#idea1 [name=what]").value = "Window composed of heat-sensitive material";
$("#idea1 [name=how]").value = "indicates the exit path";
$("#idea2 [name=what]").value = "Window made of heat-sensitive material";
$("#idea2 [name=how]").value = "shows the exit path";

fetch("/api/rules").then(r => r.json()).then(rows => {
  $("#rules").innerHTML = `<h4>v1 – the 54 rules of the paper</h4><div class="rules-wrap"><table><tr><th>ID</th><th>Pattern</th><th>Case</th><th>Condition</th><th>Output</th><th>Example</th></tr>${
    rows.map(r => `<tr><td>${r.rule_id}</td><td>${r.pattern}</td><td>${r.case}</td><td>${esc(r.condition)}</td><td>${esc(r.output)}</td><td>${esc(r.example)}</td></tr>`).join("")}</table></div>`;
});

fetch("/api/rules?version=v2").then(r => r.json()).then(rows => {
  $("#rules2").innerHTML = `<h4>v2 – corrected decision table (future work)</h4><div class="rules-wrap"><table><tr><th>ID</th><th>WHAT</th><th>HOW</th><th>Output</th><th>Condition</th></tr>${
    rows.map(r => `<tr><td>${r.rule_id}</td><td>${esc(r.WHAT)}</td><td>${esc(r.HOW)}</td><td>${esc(r.output)}</td><td>${esc(r.condition || "")}</td></tr>`).join("")}</table></div>`;
});
