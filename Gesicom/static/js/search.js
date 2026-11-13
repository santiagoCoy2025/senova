/* Búsqueda privada con cancelación, espera limitada y alternativa HTML. */
(() => {
  const dialog = document.querySelector("#command-dialog");
  const trigger = document.querySelector("#global-search");
  const fallback = document.querySelector("[data-search-fallback]");
  if (
    !dialog ||
    !trigger ||
    !fallback ||
    !dialog.showModal ||
    !window.fetch ||
    !window.AbortController
  )
    return;
  const query = dialog.querySelector("#command-query");
  const list = dialog.querySelector("#command-results");
  const status = dialog.querySelector("#command-status");
  const retry = dialog.querySelector("[data-command-retry]");
  const evidence = dialog.querySelector("[data-command-evidencias]");
  const normalize = (value) =>
    value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("es");
  const localURL = (value) => {
    if (typeof value !== "string" || !value || value.length > 2000)
      throw new Error();
    const url = new URL(value, location.origin);
    if (
      url.origin !== location.origin ||
      !/^https?:$/.test(url.protocol) ||
      url.username ||
      url.password
    )
      throw new Error();
    return url;
  };
  const readItems = (values, maximum, remote = false) => {
    if (!Array.isArray(values) || values.length > maximum) throw new Error();
    const seen = new Set();
    return values
      .map((item) => {
        if (
          !item ||
          typeof item.titulo !== "string" ||
          !item.titulo.trim() ||
          item.titulo.length > 400 ||
          typeof item.detalle !== "string" ||
          item.detalle.length > 300 ||
          (remote &&
            !["Evidencias", "Usuarios", "Plazos", "Notificaciones"].includes(
              item.tipo,
            ))
        )
          throw new Error();
        return { ...item, url: localURL(item.url).href };
      })
      .filter((item) => {
        if (seen.has(item.url)) return false;
        seen.add(item.url);
        return true;
      });
  };
  let actions, endpoint, login, evidenceURL;
  try {
    actions = readItems(
      JSON.parse(document.querySelector("#workspace-actions").textContent),
      50,
    );
    endpoint = localURL(dialog.dataset.searchUrl);
    login = localURL(dialog.dataset.loginUrl);
    evidenceURL = localURL(evidence.getAttribute("href"));
  } catch {
    return;
  }

  let active = -1,
    generation = 0,
    timer,
    timeout,
    waitTimer,
    controller;
  let waitUntil = 0,
    failure = null,
    composing = false;
  const shortcuts = () =>
    actions
      .filter((item) =>
        normalize(item.titulo).includes(normalize(query.value.trim())),
      )
      .slice(0, 8);
  const updateEvidenceLink = () => {
    const url = new URL(evidenceURL);
    if (query.value.trim()) url.searchParams.set("q", query.value.trim());
    evidence.href = url.href;
  };
  const select = (index) => {
    const items = [...list.children];
    active = items.length ? (index + items.length) % items.length : -1;
    items.forEach((item, i) =>
      item.setAttribute("aria-selected", String(i === active)),
    );
    if (active < 0) query.removeAttribute("aria-activedescendant");
    else {
      query.setAttribute("aria-activedescendant", items[active].id);
      items[active].scrollIntoView({ block: "nearest" });
    }
  };
  const render = (items) => {
    const fragment = document.createDocumentFragment();
    const seen = new Set();
    for (const item of items) {
      if (seen.has(item.url)) continue;
      seen.add(item.url);
      const index = fragment.childElementCount;
      const link = document.createElement("a");
      link.href = item.url;
      link.id = `command-option-${index}`;
      link.className = "command-option";
      link.setAttribute("role", "option");
      link.setAttribute("aria-selected", "false");
      link.tabIndex = -1;
      const symbol = document.createElement("span");
      symbol.className = "command-result-symbol";
      symbol.textContent = item.tipo ? item.tipo.slice(0, 1) : "↗";
      const text = document.createElement("span"),
        title = document.createElement("strong"),
        detail = document.createElement("small");
      title.textContent = item.titulo;
      detail.textContent = item.detalle;
      text.append(title, detail);
      link.append(symbol, text);
      link.addEventListener("pointermove", () => {
        if (active !== index) select(index);
      });
      fragment.append(link);
    }
    list.replaceChildren(fragment);
    active = -1;
    query.removeAttribute("aria-activedescendant");
    return list.childElementCount;
  };
  const syncRetry = () => {
    clearTimeout(waitTimer);
    retry.hidden = !failure;
    retry.disabled =
      !!controller || navigator.onLine === false || Date.now() < waitUntil;
    if (dialog.open && !document.hidden && Date.now() < waitUntil) {
      waitTimer = setTimeout(
        () => {
          if (failure === "limited" && Date.now() >= waitUntil)
            status.textContent =
              "Ya puedes volver a buscar. Pulsa Reintentar búsqueda.";
          syncRetry();
        },
        Math.min(waitUntil - Date.now() + 20, 2147483647),
      );
    }
  };
  const cancel = () => {
    generation++;
    clearTimeout(timer);
    timer = undefined;
    clearTimeout(timeout);
    controller?.abort();
    controller = undefined;
    list.setAttribute("aria-busy", "false");
  };
  const fail = (kind, message) => {
    failure = kind;
    status.textContent = message;
    syncRetry();
  };
  const limited = () =>
    fail(
      "limited",
      `Puedes volver a buscar en ${Math.max(1, Math.ceil((waitUntil - Date.now()) / 1000))} segundos. El botón se habilitará sin enviar otra consulta.`,
    );
  const retryDeadline = (value) => {
    if (!value) return 0;
    const seconds = /^\d+$/.test(value) ? Number(value) : NaN;
    const deadline = Number.isSafeInteger(seconds)
      ? Date.now() + seconds * 1000
      : Date.parse(value);
    return Number.isFinite(deadline) &&
      deadline > Date.now() &&
      deadline <= 8640000000000000
      ? deadline
      : 0;
  };
  const search = async () => {
    cancel();
    if (!dialog.open || document.hidden || composing) return;
    const ownGeneration = generation;
    const value = query.value.trim();
    const quick = shortcuts();
    render(quick);
    failure = null;
    syncRetry();
    updateEvidenceLink();
    if (value.length < 2) {
      status.textContent = value
        ? "Escribe al menos 2 caracteres para buscar registros."
        : "Accesos rápidos · también puedes escribir para buscar";
      return;
    }
    if (value.length > 100 || value.includes("\0")) {
      status.textContent =
        "Escribe una búsqueda válida de hasta 100 caracteres.";
      return;
    }
    if (navigator.onLine === false) {
      fail(
        "offline",
        "Estás sin conexión. Los accesos rápidos siguen disponibles; vuelve a intentarlo al conectarte.",
      );
      return;
    }
    if (Date.now() < waitUntil) {
      limited();
      return;
    }
    const ownController = new AbortController();
    controller = ownController;
    syncRetry();
    list.setAttribute("aria-busy", "true");
    status.textContent = "Buscando en tu espacio…";
    let timedOut = false;
    timeout = setTimeout(() => {
      timedOut = true;
      ownController.abort();
    }, 10000);
    try {
      const url = new URL(endpoint);
      url.searchParams.set("q", value);
      const response = await fetch(url, {
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json" },
        signal: ownController.signal,
      });
      if (ownGeneration !== generation || !dialog.open) return;
      if (response.status === 401) {
        location.assign(login.href);
        return;
      }
      if (response.status === 429) {
        waitUntil = Math.max(
          waitUntil,
          retryDeadline(response.headers.get("Retry-After")) ||
            Date.now() + 60000,
        );
        limited();
        return;
      }
      if (
        !response.ok ||
        !response.headers.get("Content-Type")?.includes("application/json")
      )
        throw new Error();
      const result = await response.json();
      if (ownGeneration !== generation || !dialog.open) return;
      const records = readItems(result?.resultados, 18, true);
      const count = render([...quick, ...records]);
      status.textContent = count
        ? `${count} resultados · usa las flechas para navegar`
        : "No encontramos resultados. Prueba con otro nombre.";
    } catch {
      if (ownGeneration === generation && dialog.open)
        fail(
          timedOut ? "timeout" : "network",
          timedOut
            ? "La búsqueda tardó demasiado. Puedes volver a intentarlo o consultar Evidencias."
            : "No pudimos completar la búsqueda. Puedes volver a intentarlo; los accesos rápidos siguen disponibles.",
        );
    } finally {
      if (ownGeneration === generation) {
        clearTimeout(timeout);
        controller = undefined;
        list.setAttribute("aria-busy", "false");
        syncRetry();
      }
    }
  };
  const queue = () => {
    cancel();
    updateEvidenceLink();
    render(shortcuts());
    failure = null;
    syncRetry();
    status.textContent = composing
      ? "Termina de escribir para buscar."
      : "Preparando búsqueda…";
    if (!composing) timer = setTimeout(search, 280);
  };
  trigger.addEventListener("click", () => {
    if (dialog.open) return;
    query.value = "";
    dialog.showModal();
    trigger.setAttribute("aria-expanded", "true");
    query.setAttribute("aria-expanded", "true");
    query.focus();
    search();
  });
  retry.addEventListener("click", () => {
    if (!retry.disabled) {
      query.focus();
      search();
    }
  });
  dialog
    .querySelector("[data-command-close]")
    .addEventListener("click", () => dialog.close());
  dialog.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !event.isComposing) {
      event.preventDefault();
      event.stopPropagation();
      dialog.close();
    }
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    cancel();
    composing = false;
    clearTimeout(waitTimer);
    query.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-expanded", "false");
    trigger.focus();
  });
  query.addEventListener("compositionstart", () => {
    composing = true;
    cancel();
  });
  query.addEventListener("compositionend", () => {
    composing = false;
    queue();
  });
  query.addEventListener("input", queue);
  query.addEventListener("keydown", (event) => {
    if (event.isComposing || composing) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      select(
        active < 0
          ? event.key === "ArrowDown"
            ? 0
            : list.children.length - 1
          : active + (event.key === "ArrowDown" ? 1 : -1),
      );
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (timer) search();
      else (list.children[active] || list.children[0])?.click();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (
      (event.ctrlKey || event.metaKey) &&
      event.key.toLowerCase() === "k" &&
      !event.isComposing
    ) {
      event.preventDefault();
      dialog.open ? dialog.close() : trigger.click();
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      clearTimeout(waitTimer);
      if (dialog.open && (controller || timer)) {
        cancel();
        fail(
          "suspended",
          "La búsqueda se detuvo al ocultar la pestaña. Puedes volver a intentarlo.",
        );
      }
    } else syncRetry();
  });
  window.addEventListener("offline", () => {
    if (dialog.open) {
      cancel();
      fail(
        "offline",
        "Estás sin conexión. Los accesos rápidos siguen disponibles; vuelve a intentarlo al conectarte.",
      );
    }
  });
  window.addEventListener("online", () => {
    if (dialog.open && failure === "offline") {
      status.textContent =
        "Conexión recuperada. Puedes volver a intentar la búsqueda.";
      syncRetry();
    }
  });
  fallback.hidden = true;
  trigger.hidden = false;
})();
