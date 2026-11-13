"use strict";
(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const notify = (message) => {
    const item = document.createElement("div");
    item.className = "toast is-error";
    item.setAttribute("role", "alert");
    item.textContent = message;
    $("#toast-region")?.append(item);
    setTimeout(() => item.remove(), 6500);
  };
  const refreshSelection = (form) => {
    const controls = $$("input[name=usuarios]:not(:disabled)", form);
    const count = controls.filter((input) => input.checked).length;
    $("[data-selection-count]", form).textContent = `${count} seleccionada${count === 1 ? "" : "s"}`;
    const all = $("[data-select-all]", form);
    all.checked = count > 0 && count === controls.length;
    all.indeterminate = count > 0 && count < controls.length;
    all.disabled = !controls.length;
    $$("[data-selection-action]", form).forEach((button) => {
      button.disabled = !count;
    });
  };
  const initialize = () => $$("[data-account-actions]").forEach(refreshSelection);
  initialize();
  document.addEventListener("workspace:updated", initialize);
  document.addEventListener("change", (event) => {
    const form = event.target.closest("[data-account-actions]");
    if (!form) return;
    if (event.target.matches("[data-select-all]")) {
      $$("input[name=usuarios]:not(:disabled)", form).forEach((input) => {
        input.checked = event.target.checked;
      });
    }
    refreshSelection(form);
  });
  const refreshNotices = () => {
    const form = $("[data-notice-selection]");
    if (!form) return;
    const controls = [...form.elements].filter((el) => el.name === "avisos");
    const count = controls.filter((el) => el.checked).length;
    $("[data-notice-count]", form).textContent = `${count} seleccionados`;
    const all = $("[data-notice-all]", form);
    all.checked = count > 0 && count === controls.length;
    all.indeterminate = count > 0 && count < controls.length;
    $$("[data-notice-action]", form).forEach((button) => { button.disabled = !count; });
  };
  refreshNotices();
  document.addEventListener("workspace:updated", refreshNotices);
  document.addEventListener("change", (event) => {
    if (event.target.matches("[data-notice-all]")) {
      [...event.target.form.elements].filter((el) => el.name === "avisos").forEach((el) => {
        el.checked = event.target.checked;
      });
    }
    if (event.target.matches("[data-notice-all], input[name=avisos]")) refreshNotices();
  });
  const permissionForm = $("[data-permission-editor]");
  if (permissionForm) {
    const choices = $$("select[name^=perm_]", permissionForm);
    const initial = new Map(choices.map((field) => [field.name, field.value]));
    permissionForm.addEventListener("change", () => {
      const count = choices.filter((field) => field.value !== initial.get(field.name)).length;
      $("[data-permission-status]", permissionForm).textContent = count ?
        `${count} cambio(s) por guardar. Se aplicarán a todo el grupo.` : "Los permisos no tienen cambios.";
    });
  }
  const confirmation = $("#account-confirm");
  const approved = new WeakSet();
  let pending;
  document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-account-actions]");
    if (!form || !confirmation || !confirmation.showModal) return;
    if (approved.has(form)) {
      approved.delete(form);
      delete form.dataset.dirty;
      return;
    }
    event.preventDefault();
    const button = event.submitter;
    const action = button?.value || "roles";
    const count = action === "roles" ?
      $$("select[name^=role_]", form).filter((input) => input.value !== "__keep__").length :
      $$("input[name=usuarios]:checked", form).length;
    if (!count) {
      notify(action === "roles" ? "Selecciona al menos un cambio de rol." :
        "Selecciona al menos una cuenta.");
      return;
    }
    pending = {
      form,
      button
    };
    $("[data-confirm-description]", confirmation).textContent = action === "roles" ?
      `Vas a actualizar los roles de ${count} cuenta(s). Los roles elegidos sustituirán los actuales.` :
      `Vas a ${action} ${count} cuenta(s).`;
    confirmation.showModal();
    $("[data-account-cancel]", confirmation).focus();
  });
  if (confirmation) {
    $("[data-account-cancel]", confirmation).addEventListener("click", () => confirmation.close());
    $("[data-account-accept]", confirmation).addEventListener("click", () => {
      const {
        form,
        button
      } = pending;
      approved.add(form);
      confirmation.close("accepted");
      form.requestSubmit(button);
    });
    confirmation.addEventListener("close", () => {
      if (confirmation.returnValue !== "accepted" && pending) $("[name=contrasena_actual]", pending
        .form).value = "";
      confirmation.returnValue = "";
      pending = null;
    });
  }
})();
