const apiParam = new URLSearchParams(window.location.search).get("api");
localStorage.removeItem("aviva_api_base");
const isLocalHost = ["127.0.0.1", "localhost"].includes(window.location.hostname);
const API_BASE = apiParam || window.AVIVA_API_BASE || (isLocalHost ? "http://127.0.0.1:8000" : window.location.origin);

const state = {
  memberToken: localStorage.getItem("aviva_member_token"),
  adminToken: localStorage.getItem("aviva_admin_token"),
};

const $ = (selector, root = document) => root.querySelector(selector);

const formatDate = (dateValue) => {
  const date = new Date(`${dateValue}T00:00:00`);
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "long", year: "numeric" }).format(date);
};

const setMessage = (text, isError = false) => {
  const message = $(".message");
  if (!message) return;
  message.textContent = text || "";
  message.classList.toggle("error", isError);
};

const showLoginGreeting = (name) => {
  const greeting = $("[data-login-greeting]");
  if (!greeting) {
    setMessage(`Ola, ${name}`);
    return;
  }

  const nameTarget = $("[data-login-name]", greeting);
  if (nameTarget) nameTarget.textContent = name;

  greeting.hidden = false;
  $("form[data-login]")?.setAttribute("hidden", "");
  $(".auth-links")?.setAttribute("hidden", "");
  setMessage("");
};

const request = async (path, options = {}) => {
  let response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
        ...options.headers,
      },
      ...options,
    });
  } catch {
    throw new Error("Nao foi possivel conectar com a API.");
  }

  if (!response.ok) {
    let detail = "Não foi possível concluir a ação.";
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
};

const imageFileToDataUrl = (file) => new Promise((resolve, reject) => {
  const image = new Image();
  const reader = new FileReader();

  reader.onerror = () => reject(new Error("Nao foi possivel ler a imagem."));
  reader.onload = () => {
    image.onerror = () => reject(new Error("Nao foi possivel carregar a imagem."));
    image.onload = () => {
      const maxSize = 1400;
      const scale = Math.min(1, maxSize / Math.max(image.width, image.height));
      const width = Math.max(1, Math.round(image.width * scale));
      const height = Math.max(1, Math.round(image.height * scale));
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;

      const context = canvas.getContext("2d");
      context.drawImage(image, 0, 0, width, height);
      resolve(canvas.toDataURL("image/jpeg", 0.82));
    };
    image.src = String(reader.result);
  };

  reader.readAsDataURL(file);
});

const login = async () => {
  const form = $("form[data-login]");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("Entrando...");

    const data = Object.fromEntries(new FormData(form).entries());

    try {
      const payload = await request("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: data.email, password: data.password }),
      });

      const userName = payload.name || data.email;
      localStorage.setItem("aviva_user_name", userName);
      showLoginGreeting(userName);

      const redirectTo = payload.role === "admin" ? "/admin/" : "/membros/";

      if (payload.role === "admin") {
        localStorage.setItem("aviva_admin_token", payload.access_token);
        localStorage.removeItem("aviva_member_token");
      } else {
        localStorage.setItem("aviva_member_token", payload.access_token);
        localStorage.removeItem("aviva_admin_token");
      }

      window.setTimeout(() => {
        window.location.href = redirectTo;
      }, 900);
    } catch (error) {
      setMessage(error.message, true);
    }
  });
};

const registerMember = async () => {
  const form = $("form[data-register]");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("Criando cadastro...");

    const data = Object.fromEntries(new FormData(form).entries());

    try {
      const payload = await request("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          name: data.name,
          email: data.email,
          password: data.password,
        }),
      });
      localStorage.setItem("aviva_member_token", payload.access_token);
      localStorage.setItem("aviva_user_name", payload.name || data.name);
      window.location.href = "/membros/";
    } catch (error) {
      setMessage(error.message, true);
    }
  });
};

const logout = (role) => {
  if (role === "admin") {
    localStorage.removeItem("aviva_admin_token");
    localStorage.removeItem("aviva_user_name");
    window.location.href = "/community/";
    return;
  }
  localStorage.removeItem("aviva_member_token");
  localStorage.removeItem("aviva_user_name");
  window.location.href = "/community/";
};

const protect = (role) => {
  const token = role === "admin" ? state.adminToken : state.memberToken || state.adminToken;
  if (!token) {
    window.location.href = "/community/";
  }
  return token;
};

const eventImage = (eventItem) => eventItem.image_url || "/assets/IMG_6893.jpeg";

const eventCard = (eventItem, admin = false) => {
  const article = document.createElement("article");
  article.className = admin ? "admin-row" : "event-card";

  if (admin) {
    article.innerHTML = `
      <div>
        <h3>${eventItem.title}</h3>
        <p class="muted">${formatDate(eventItem.date)} - ${eventItem.start_time} às ${eventItem.end_time} - ${eventItem.location}</p>
      </div>
      <div class="actions">
        <a class="btn btn-secondary" href="/admin/eventos/editar/?id=${eventItem.id}">Editar</a>
        <button class="btn btn-danger" data-delete="${eventItem.id}">Excluir</button>
      </div>
    `;
    return article;
  }

  article.innerHTML = `
    <img src="${eventImage(eventItem)}" alt="">
    <div class="event-body">
      <h3>${eventItem.title}</h3>
      <div class="event-meta">
        <span>${formatDate(eventItem.date)}</span>
        <span>${eventItem.start_time} às ${eventItem.end_time}</span>
        <span>${eventItem.location}</span>
      </div>
      <p class="muted">${eventItem.description}</p>
      <div class="actions">
        <a class="btn btn-primary" href="${API_BASE}/events/${eventItem.id}/ics">Adicionar à agenda</a>
      </div>
    </div>
  `;
  return article;
};

const renderEvents = async ({ containerId, limit, countId } = {}) => {
  const container = $(`#${containerId}`);
  if (!container) return;

  try {
    const events = await request("/events");
    if (countId && $(`#${countId}`)) $(`#${countId}`).textContent = events.length;
    container.innerHTML = "";

    events.slice(0, limit || events.length).forEach((eventItem) => {
      container.appendChild(eventCard(eventItem));
    });

    if (!events.length) {
      container.innerHTML = '<div class="empty-state">Nenhum evento cadastrado ainda.</div>';
    }
  } catch (error) {
    container.innerHTML = `<div class="empty-state">${error.message}</div>`;
  }
};

const loadMemberHome = async () => {
  protect("member");
  const container = $("#events-preview");
  if (!container) return;

  try {
    const events = await request("/events");
    $("#event-count").textContent = events.length;
    $("#next-event").textContent = events[0] ? formatDate(events[0].date) : "Sem eventos";
    container.innerHTML = "";
    events.slice(0, 3).forEach((eventItem) => container.appendChild(eventCard(eventItem)));
    if (!events.length) container.innerHTML = '<div class="empty-state">Nenhum evento cadastrado ainda.</div>';
  } catch (error) {
    container.innerHTML = `<div class="empty-state">${error.message}</div>`;
  }
};

const loadEvents = async () => {
  if (document.body.dataset.page === "member-events") protect("member");
  renderEvents({ containerId: "events-list", countId: "public-event-count" });
};

const loadAdmin = async () => {
  const token = protect("admin");
  const container = $("#admin-events");
  if (!container) return;

  try {
    const events = await request("/admin/events", { token });
    $("#admin-event-count").textContent = events.length;
    container.innerHTML = "";
    events.forEach((eventItem) => container.appendChild(eventCard(eventItem, true)));
    if (!events.length) container.innerHTML = '<div class="empty-state">Nenhum evento cadastrado ainda.</div>';

    container.querySelectorAll("[data-delete]").forEach((button) => {
      button.addEventListener("click", async () => {
        if (!confirm("Excluir este evento?")) return;
        await request(`/admin/events/${button.dataset.delete}`, { method: "DELETE", token });
        loadAdmin();
      });
    });
  } catch (error) {
    container.innerHTML = `<div class="empty-state">${error.message}</div>`;
  }
};

const bindEventForm = async () => {
  const token = protect("admin");
  const form = $("form[data-event-form]");
  if (!form) return;

  const params = new URLSearchParams(window.location.search);
  const id = params.get("id");

  if (id) {
    try {
      const eventItem = await request(`/admin/events/${id}`, { token });
      Object.entries(eventItem).forEach(([key, value]) => {
        const input = form.elements[key];
        if (input && value !== null) input.value = value;
      });
    } catch (error) {
      setMessage(error.message, true);
    }
  }

  const fileInput = form.elements.image_file;
  const preview = $("#event-image-preview");
  const existingUrlInput = form.elements.image_url;

  const updatePreview = (src) => {
    if (!preview || !src) return;
    preview.src = src;
    preview.hidden = false;
  };

  if (existingUrlInput?.value) updatePreview(existingUrlInput.value);

  fileInput?.addEventListener("change", () => {
    const file = fileInput.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setMessage("Escolha um arquivo de imagem.", true);
      fileInput.value = "";
      return;
    }

    imageFileToDataUrl(file)
      .then(updatePreview)
      .catch((error) => setMessage(error.message, true));
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("Salvando evento...");
    const payload = Object.fromEntries(new FormData(form).entries());
    delete payload.image_file;
    payload.image_url = payload.image_url || null;

    try {
      const file = fileInput?.files?.[0];
      if (file) {
        payload.image_url = await imageFileToDataUrl(file);
      }

      await request(id ? `/admin/events/${id}` : "/admin/events", {
        method: id ? "PUT" : "POST",
        token,
        body: JSON.stringify(payload),
      });
      window.location.href = "/admin/";
    } catch (error) {
      setMessage(error.message, true);
    }
  });
};

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;

  document.querySelectorAll("[data-logout]").forEach((button) => {
    button.addEventListener("click", () => logout(button.dataset.logout));
  });

  if ($("#events-preview") && !page) renderEvents({ containerId: "events-preview", limit: 3 });
  if (page === "community-login" || page === "member-login" || page === "admin-login") login();
  if (page === "member-register") registerMember();
  if (page === "member-home") loadMemberHome();
  if (page === "member-events" || page === "public-events") loadEvents();
  if (page === "admin-home") loadAdmin();
  if (page === "admin-event-form") bindEventForm();
});
