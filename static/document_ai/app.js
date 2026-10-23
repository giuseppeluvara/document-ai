(() => {
  "use strict";

  const fileInput = document.querySelector('input[type="file"]');
  const fileInfo = document.querySelector("[data-file-info]");
  if (fileInput && fileInfo) {
    fileInput.addEventListener("change", () => {
      const file = fileInput.files[0];
      fileInfo.textContent = file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB` : "Nessun file selezionato";
    });
  }

  for (const form of document.querySelectorAll("form[data-confirm]")) {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  }

  for (const link of document.querySelectorAll("[data-source-target]")) {
    link.addEventListener("click", () => {
      const source = document.getElementById(link.dataset.sourceTarget);
      if (source && source.tagName === "DETAILS") source.open = true;
    });
  }
  if (location.hash) {
    const target = document.getElementById(location.hash.slice(1));
    if (target && target.tagName === "DETAILS") target.open = true;
  }

  const templateForm = document.querySelector("[data-template-form]");
  if (templateForm) setupFieldEditor(templateForm);

  for (const form of document.querySelectorAll("[data-busy-form]")) {
    form.addEventListener("submit", (event) => {
      if (event.defaultPrevented) return;
      for (const button of form.querySelectorAll('button[type="submit"]')) {
        if (button.dataset.busyLabel) button.textContent = button.dataset.busyLabel;
        button.disabled = true;
      }
      form.setAttribute("aria-busy", "true");
    });
  }

  const statusRoot = document.querySelector("[data-poll-status-url]");
  if (statusRoot && ["queued", "processing"].includes(statusRoot.dataset.documentStatus)) {
    const pollMessage = document.querySelector("[data-poll-message]");
    const current = statusRoot.dataset.documentStatus;
    let failures = 0;
    const poll = async () => {
      if (document.hidden) {
        window.setTimeout(poll, 4000);
        return;
      }
      try {
        const response = await fetch(statusRoot.dataset.pollStatusUrl, {credentials: "same-origin", headers: {Accept: "application/json"}});
        if (!response.ok) throw new Error("status unavailable");
        const data = await response.json();
        failures = 0;
        if (data.status !== current) {
          location.reload();
          return;
        }
        if (pollMessage) pollMessage.textContent = "Aggiornamento automatico attivo";
      } catch (_) {
        failures += 1;
        if (pollMessage) pollMessage.textContent = "Connessione momentaneamente non disponibile. Nuovo tentativo in corso…";
      }
      window.setTimeout(poll, Math.min(3000 * (failures + 1), 15000));
    };
    window.setTimeout(poll, 3000);
  }

  function setupFieldEditor(form) {
    const source = form.querySelector('[name="fields_json"]');
    const editor = form.querySelector("[data-field-editor]");
    const rawEditor = form.querySelector("[data-json-editor]");
    const addButton = form.querySelector("[data-add-field]");
    const counter = form.querySelector("[data-field-count]");
    const error = form.querySelector("[data-editor-error]");
    if (!source || !editor || !rawEditor || !addButton) return;
    let fields;
    try {
      fields = JSON.parse(source.value || "[]");
      if (!Array.isArray(fields) || fields.some(field => !field || typeof field !== "object" || Array.isArray(field))) return;
    } catch (_) {
      return;
    }
    if (!fields.length) fields.push({key: "", label: "", description: "", type: "text"});
    editor.hidden = false;
    rawEditor.hidden = true;
    addButton.hidden = false;

    const sync = () => {
      source.value = JSON.stringify(fields.map(field => ({key: field.key || "", label: field.label || "", description: field.description || "", type: field.type || "text"})));
      addButton.disabled = fields.length >= 12;
      if (counter) counter.textContent = `${fields.length} / 12 campi`;
    };

    const slug = (value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 64);

    const createControl = (labelText, control, className) => {
      const wrapper = document.createElement("div");
      if (className) wrapper.className = className;
      const label = document.createElement("label");
      label.htmlFor = control.id;
      label.textContent = labelText;
      wrapper.append(label, control);
      return wrapper;
    };

    const makeInput = (index, property, maxLength) => {
      const input = document.createElement("input");
      input.type = "text";
      input.id = `editor-${index}-${property}`;
      input.value = fields[index][property] || "";
      input.maxLength = maxLength;
      input.required = true;
      input.addEventListener("input", () => {
        fields[index][property] = input.value;
        sync();
      });
      return input;
    };

    const render = (focusIndex) => {
      editor.replaceChildren();
      fields.forEach((field, index) => {
        const row = document.createElement("section");
        row.className = "editor-row";
        row.setAttribute("aria-label", `Campo ${index + 1}`);
        const top = document.createElement("div");
        top.className = "editor-row-top";
        const number = document.createElement("span");
        number.className = "editor-row-number";
        number.textContent = `CAMPO ${String(index + 1).padStart(2, "0")}`;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "editor-delete";
        remove.textContent = "Rimuovi";
        remove.setAttribute("aria-label", `Rimuovi campo ${index + 1}`);
        remove.disabled = fields.length === 1;
        remove.addEventListener("click", () => {
          fields.splice(index, 1);
          render(Math.max(0, index - 1));
        });
        top.append(number, remove);
        const grid = document.createElement("div");
        grid.className = "editor-row-grid";
        const labelInput = makeInput(index, "label", 80);
        labelInput.placeholder = "Es. Importo del contratto";
        const keyInput = makeInput(index, "key", 64);
        keyInput.pattern = "[a-z][a-z0-9_]*";
        keyInput.title = "Inizia con una lettera minuscola. Usa lettere minuscole, numeri e underscore.";
        keyInput.placeholder = "importo_contratto";
        keyInput.spellcheck = false;
        let autoKey = !field.key;
        keyInput.addEventListener("input", () => { autoKey = false; });
        labelInput.addEventListener("input", () => {
          if (autoKey) {
            let nextKey = slug(labelInput.value);
            if (nextKey && !/^[a-z]/.test(nextKey)) nextKey = `campo_${nextKey}`.slice(0, 64);
            keyInput.value = nextKey;
            field.key = nextKey;
            sync();
          }
        });
        const type = document.createElement("select");
        type.id = `editor-${index}-type`;
        for (const [value, label] of [["text", "Testo"], ["number", "Numero"], ["date", "Data"], ["list", "Elenco"]]) {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = label;
          option.selected = (field.type || "text") === value;
          type.append(option);
        }
        type.addEventListener("change", () => { field.type = type.value; sync(); });
        grid.append(createControl("Nome del campo", labelInput), createControl("Chiave export", keyInput), createControl("Tipo", type));
        const description = document.createElement("textarea");
        description.id = `editor-${index}-description`;
        description.value = field.description || "";
        description.maxLength = 240;
        description.rows = 2;
        description.placeholder = "Descrivi l’informazione da cercare e gli eventuali elementi da escludere.";
        description.addEventListener("input", () => { field.description = description.value; sync(); });
        row.append(top, grid, createControl("Istruzioni per l’estrazione", description, "editor-description"));
        editor.append(row);
      });
      sync();
      if (focusIndex !== undefined) editor.querySelector(`#editor-${focusIndex}-label`)?.focus();
    };

    addButton.addEventListener("click", () => {
      if (fields.length >= 12) return;
      fields.push({key: "", label: "", description: "", type: "text"});
      render(fields.length - 1);
    });
    form.addEventListener("submit", (event) => {
      sync();
      const keys = fields.map(field => field.key);
      if (new Set(keys).size !== keys.length) {
        event.preventDefault();
        if (error) {
          error.hidden = false;
          error.textContent = "Ogni campo deve avere una chiave export diversa.";
          error.scrollIntoView({block: "center"});
        }
      }
    });
    render();
  }
})();
