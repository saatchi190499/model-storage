const toast = document.getElementById("toast");
const treeView = document.getElementById("tree-view");
const filesTableBody = document.getElementById("files-table-body");
const fileVersionsTableBody = document.getElementById("file-versions-table-body");
const versionsTableBody = document.getElementById("versions-table-body");
const tableFoot = document.getElementById("table-foot");
const fileVersionsFoot = document.getElementById("file-versions-foot");
const versionsFoot = document.getElementById("versions-foot");
const logBody = document.getElementById("log-body");
const titleContext = document.getElementById("title-context");
const selectedFieldEl = document.getElementById("selected-field");
const selectedProjectEl = document.getElementById("selected-project");
const dialogBackdrop = document.getElementById("dialog-backdrop");
const actionDialog = document.getElementById("action-dialog");
const dialogTitle = document.getElementById("dialog-title");
const dialogFields = document.getElementById("dialog-fields");
const dialogCancel = document.getElementById("dialog-cancel");
const zipFileInput = document.getElementById("zip-file-input");
const projectActionButtons = document.querySelectorAll('[data-role="project-action"]');

const state = {
  fields: [],
  projects: [],
  files: [],
  fileVersions: [],
  commitVersions: [],
  selectedFieldId: "",
  selectedProjectId: "",
  selectedFileVersionId: null,
  selectedVersionCommitId: null,
  expandedFieldIds: new Set(),
  currentPath: "",
};

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.remove("hidden", "error");
  if (isError) toast.classList.add("error");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 3000);
}

function log(message, level = "Info") {
  const tr = document.createElement("tr");
  const now = new Date();
  const stamp = `${String(now.getDate()).padStart(2, "0")}/${String(now.getMonth() + 1).padStart(2, "0")}/${now.getFullYear()} ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
  tr.innerHTML = `<td>${stamp}</td><td>${level}</td><td>${message}</td>`;
  logBody.prepend(tr);
  while (logBody.children.length > 120) logBody.removeChild(logBody.lastChild);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get("content-type") || "";
  let payload = null;

  if (contentType.includes("application/json")) payload = await response.json();
  else if (!options.expectBlob) payload = await response.text();

  if (!response.ok) {
    const message = payload?.detail || payload?.message || response.statusText;
    throw new Error(message);
  }

  if (options.expectBlob) return response.blob();
  return payload;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function ensureSelectedProject() {
  if (!state.selectedProjectId) throw new Error("Select a project first.");
  return state.selectedProjectId;
}

function ensureSelectedVersionCommit() {
  if (!state.selectedVersionCommitId) throw new Error("Select a commit version first.");
  return state.selectedVersionCommitId;
}

function selectedFieldName() {
  return state.fields.find((f) => f.id === state.selectedFieldId)?.name || "";
}

function selectedProjectName() {
  return state.projects.find((p) => p.id === state.selectedProjectId)?.name || "";
}

function setSelected(fieldId, projectId) {
  if (fieldId !== undefined) state.selectedFieldId = fieldId;
  if (projectId !== undefined) state.selectedProjectId = projectId;

  selectedFieldEl.textContent = selectedFieldName() || state.selectedFieldId || "none";
  selectedProjectEl.textContent = selectedProjectName() || state.selectedProjectId || "none";
  for (const button of projectActionButtons) {
    button.classList.toggle("hidden", !state.selectedFieldId);
  }
  if (selectedProjectName()) titleContext.textContent = `Project: ${selectedProjectName()}`;
  else if (selectedFieldName()) titleContext.textContent = `Field: ${selectedFieldName()}`;
  else titleContext.textContent = "Select field";
}

function fieldOptions() {
  return state.fields.map((field) => ({ value: field.id, label: field.name }));
}

function projectOptions() {
  return state.projects.map((project) => ({ value: project.id, label: project.name }));
}

function resetCommitVersions() {
  state.commitVersions = [];
  state.selectedVersionCommitId = null;
  renderCommitVersions();
}

function resetFileVersions() {
  state.fileVersions = [];
  state.selectedFileVersionId = null;
  renderFileVersions();
}

function renderTree() {
  treeView.innerHTML = "";

  if (!state.fields.length) {
    treeView.innerHTML = "<li class='tree-item'>No fields found. Create one from toolbar.</li>";
    return;
  }

  for (const field of state.fields) {
    const expanded = state.expandedFieldIds.has(field.id);
    const fieldLi = document.createElement("li");
    fieldLi.className = `tree-item${state.selectedFieldId === field.id ? " active" : ""}`;
    fieldLi.textContent = `${expanded ? "-" : "+"} Field: ${field.name}`;
    fieldLi.title = field.id;
    fieldLi.addEventListener("click", async () => {
      try {
        setSelected(field.id, "");
        if (expanded) {
          state.expandedFieldIds.delete(field.id);
          renderTree();
          return;
        }
        state.expandedFieldIds.add(field.id);
        await listProjects(field.id, true);
        state.files = [];
        renderFiles();
        resetFileVersions();
        resetCommitVersions();
        renderTree();
        log(`Expanded field ${field.name}`);
      } catch (error) {
        showToast(error.message, true);
        log(error.message, "Error");
      }
    });
    treeView.appendChild(fieldLi);

    if (!expanded) continue;

    for (const project of state.projects.filter((item) => item.field_id === field.id)) {
      const projectLi = document.createElement("li");
      projectLi.className = `tree-item${state.selectedProjectId === project.id ? " active" : ""}`;
      projectLi.textContent = `   Project: ${project.name}`;
      projectLi.title = project.id;
      projectLi.addEventListener("click", async () => {
        try {
          setSelected(field.id, project.id);
          await browseFiles(project.id);
          await loadCommitVersions(project.id, true);
          renderTree();
          log(`Opened project ${project.name}`);
        } catch (error) {
          showToast(error.message, true);
          log(error.message, "Error");
        }
      });
      treeView.appendChild(projectLi);
    }
  }
}

function renderFiles() {
  filesTableBody.innerHTML = "";
  for (const file of state.files) {
    const tr = document.createElement("tr");
    if (file.file_version_id && state.selectedFileVersionId === file.file_version_id) tr.classList.add("selected-row");
    const isFolder = file.type === "folder" || file.file_format === "folder";
    const updatedAt = file.updated_at ? new Date(file.updated_at).toLocaleString() : "";
    tr.innerHTML = `<td>${file.file_version_id ?? "-"}</td><td>${file.name || ""}</td><td>${file.file_format || (isFolder ? "folder" : "")}</td><td>${updatedAt}</td>`;
    if (isFolder) {
      tr.addEventListener("click", async () => {
        try {
          const projectId = ensureSelectedProject();
          const nextPath = state.currentPath ? `${state.currentPath}/${file.name}` : file.name;
          await browseFiles(projectId, nextPath);
        } catch (error) {
          showToast(error.message, true);
          log(error.message, "Error");
        }
      });
    } else if (file.file_version_id) {
      tr.addEventListener("click", async () => {
        try {
          state.selectedFileVersionId = file.file_version_id;
          renderFiles();
          await loadFileVersions(file.file_version_id, true);
        } catch (error) {
          showToast(error.message, true);
          log(error.message, "Error");
        }
      });
    }
    filesTableBody.appendChild(tr);
  }
  tableFoot.textContent = `Items: ${state.files.length}`;
}

function renderFileVersions() {
  fileVersionsTableBody.innerHTML = "";
  for (const version of state.fileVersions) {
    const tr = document.createElement("tr");
    if (state.selectedFileVersionId === version.file_version_id) tr.classList.add("selected-row");
    tr.innerHTML = `<td>${version.file_version_id}</td><td>v${version.version}</td><td>${version.commit_id}</td><td>${version.file_size}</td>`;
    tr.addEventListener("click", () => {
      state.selectedFileVersionId = version.file_version_id;
      state.selectedVersionCommitId = version.commit_id;
      renderFileVersions();
      renderCommitVersions();
      showToast(`Selected file version ${version.file_version_id} (commit ${version.commit_id})`);
    });
    fileVersionsTableBody.appendChild(tr);
  }
  fileVersionsFoot.textContent = `File Versions: ${state.fileVersions.length}`;
}

function renderCommitVersions() {
  versionsTableBody.innerHTML = "";
  for (const commit of state.commitVersions) {
    const tr = document.createElement("tr");
    if (state.selectedVersionCommitId === commit.id) tr.classList.add("selected-row");
    const created = new Date(commit.created_at).toLocaleString();
    tr.innerHTML = `<td>${commit.id}</td><td>${commit.message || ""}</td><td>${commit.user_id}</td><td>${commit.is_complete ? "Yes" : "No"}</td><td>${created}</td>`;
    tr.addEventListener("click", () => {
      state.selectedVersionCommitId = commit.id;
      renderCommitVersions();
      showToast(`Selected commit version #${commit.id}`);
    });
    versionsTableBody.appendChild(tr);
  }
  versionsFoot.textContent = `Versions: ${state.commitVersions.length}`;
}

function openDialog(title, fields, onSubmit) {
  dialogTitle.textContent = title;
  dialogFields.innerHTML = "";

  for (const field of fields) {
    const label = document.createElement("label");
    label.textContent = field.label;

    if (field.type === "select") {
      const select = document.createElement("select");
      select.name = field.name;
      select.required = !!field.required;
      for (const option of field.options || []) {
        const el = document.createElement("option");
        el.value = option.value;
        el.textContent = option.label;
        if (String(option.value) === String(field.value)) el.selected = true;
        select.appendChild(el);
      }
      label.appendChild(select);
    } else {
      const input = document.createElement("input");
      input.type = field.type || "text";
      input.name = field.name;
      input.required = !!field.required;
      input.value = field.value || "";
      label.appendChild(input);
    }

    dialogFields.appendChild(label);
  }

  dialogBackdrop.classList.remove("hidden");
  const firstField = dialogFields.querySelector("input,select");
  if (firstField) firstField.focus();

  actionDialog.onsubmit = async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(actionDialog).entries());
    try {
      await onSubmit(values);
      dialogBackdrop.classList.add("hidden");
    } catch (error) {
      showToast(error.message, true);
      log(error.message, "Error");
    }
  };
}

dialogCancel.addEventListener("click", () => dialogBackdrop.classList.add("hidden"));
dialogBackdrop.addEventListener("click", (event) => {
  if (event.target === dialogBackdrop) dialogBackdrop.classList.add("hidden");
});

async function listFields(silent = false) {
  state.fields = await api("/field/");
  state.projects = [];
  setSelected("", "");
  renderTree();
  if (!silent) showToast("Fields loaded");
  log(`Loaded ${state.fields.length} field(s)`);
}

async function createField(values) {
  await api("/field/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: values.name, description: values.description }),
  });
  await listFields(true);
  renderTree();
  showToast("Field created");
  log(`Created field ${values.name}`);
}

async function listProjects(fieldId, silent = false) {
  const loaded = await api(`/project/s/${fieldId}`);
  state.projects = state.projects.filter((item) => item.field_id !== fieldId).concat(loaded);
  setSelected(fieldId, "");
  renderTree();
  if (!silent) showToast("Projects loaded");
  log(`Loaded ${loaded.length} project(s)`);
}

async function createProject(values) {
  await api("/project/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      field_id: values.field_id,
      name: values.name,
      description: values.description,
      is_private: values.is_private === "true",
    }),
  });
  state.expandedFieldIds.add(values.field_id);
  await listProjects(values.field_id, true);
  renderTree();
  showToast("Project created");
  log(`Created project ${values.name}`);
}

async function deleteField(fieldId) {
  await api(`/field/s/${fieldId}`, { method: "DELETE" });
  state.projects = state.projects.filter((item) => item.field_id !== fieldId);
  state.expandedFieldIds.delete(fieldId);
  state.files = [];
  if (state.selectedFieldId === fieldId) setSelected("", "");
  await listFields(true);
  renderFiles();
  resetFileVersions();
  resetCommitVersions();
  showToast("Field deleted");
  log(`Deleted field ${fieldId}`);
}

async function deleteProject(projectId) {
  await api(`/project/${projectId}`, { method: "DELETE" });
  state.projects = state.projects.filter((item) => item.id !== projectId);
  state.files = [];
  if (state.selectedProjectId === projectId) setSelected(state.selectedFieldId, "");
  renderTree();
  renderFiles();
  resetFileVersions();
  resetCommitVersions();
  showToast("Project deleted");
  log(`Deleted project ${projectId}`);
}

async function browseFiles(projectId, path = "") {
  const query = path ? `?path=${encodeURIComponent(path)}` : "";
  state.files = await api(`/file/${projectId}${query}`);
  state.currentPath = path;
  renderFiles();
  resetFileVersions();
  showToast("Files loaded");
  log(`Loaded ${state.files.length} file(s)`);
}

async function loadFileVersions(fileVersionId, silent = false) {
  state.fileVersions = await api(`/file/version-history/${fileVersionId}`);
  const selected = state.fileVersions.find((item) => item.file_version_id === fileVersionId) || state.fileVersions[0];
  if (selected) {
    state.selectedFileVersionId = selected.file_version_id;
    state.selectedVersionCommitId = selected.commit_id;
  }
  renderFileVersions();
  renderCommitVersions();
  if (!silent) showToast(`Loaded ${state.fileVersions.length} file version(s)`);
  log(`Loaded ${state.fileVersions.length} file version(s)`);
}

async function loadCommitVersions(projectId, silent = false) {
  state.commitVersions = await api(`/commit/history/${projectId}`);
  state.selectedVersionCommitId = state.commitVersions[0]?.id || null;
  renderCommitVersions();
  if (!silent) showToast(`Loaded ${state.commitVersions.length} commit version(s)`);
  log(`Loaded ${state.commitVersions.length} commit version(s) for project ${projectId}`);
}

async function filesAtCommit(commitId) {
  state.files = await api(`/file/files/${commitId}`);
  state.currentPath = `commit/${commitId}`;
  renderFiles();
  showToast("Commit files loaded");
  log(`Loaded files at commit ${commitId}`);
}

async function uploadCommit(projectId, message) {
  const file = zipFileInput.files?.[0];
  if (!file) throw new Error("Select a ZIP file first");
  const form = new FormData();
  form.set("project_id", projectId);
  form.set("message", message || "");
  form.set("file", file);
  await api(`/commit/${projectId}`, { method: "POST", body: form });
  await browseFiles(projectId, state.currentPath || "");
  await loadCommitVersions(projectId, true);
  showToast("Commit uploaded");
  log(`Uploaded commit to project ${projectId}`);
}

async function downloadProject(projectId) {
  const blob = await api(`/${projectId}`, { expectBlob: true });
  downloadBlob(blob, `project-${projectId}.zip`);
  showToast("Project ZIP downloaded");
  log(`Downloaded latest ZIP for project ${projectId}`);
}

async function downloadCommit(commitId) {
  const blob = await api(`/files/${commitId}`, { expectBlob: true });
  downloadBlob(blob, `commit-${commitId}.zip`);
  showToast("Commit ZIP downloaded");
  log(`Downloaded commit ZIP ${commitId}`);
}

async function handleAction(action) {
  if (action === "new-field") {
    openDialog(
      "Create Field",
      [
        { name: "name", label: "Name", required: true },
        { name: "description", label: "Description", required: true },
      ],
      createField,
    );
    return;
  }

  if (action === "list-projects") {
    if (!state.fields.length) throw new Error("No fields found.");
    const defaultFieldId = state.selectedFieldId || state.fields[0].id;
    openDialog(
      "List Projects",
      [{ name: "field_id", label: "Field", type: "select", required: true, value: defaultFieldId, options: fieldOptions() }],
      async (values) => listProjects(values.field_id),
    );
    return;
  }

  if (action === "new-project") {
    if (!state.fields.length) throw new Error("No fields loaded. Create a field first.");
    const defaultFieldId = state.selectedFieldId || state.fields[0].id;
    openDialog(
      "Create Project",
      [
        { name: "field_id", label: "Field", type: "select", required: true, value: defaultFieldId, options: fieldOptions() },
        { name: "name", label: "Name", required: true },
        { name: "description", label: "Description", required: true },
        { name: "is_private", label: "Is Private (true/false)", required: true, value: "false" },
      ],
      createProject,
    );
    return;
  }

  if (action === "delete-field") {
    if (!state.fields.length) throw new Error("No fields to delete.");
    const defaultFieldId = state.selectedFieldId || state.fields[0].id;
    openDialog(
      "Delete Field",
      [{ name: "field_id", label: "Field", type: "select", required: true, value: defaultFieldId, options: fieldOptions() }],
      async (values) => deleteField(values.field_id),
    );
    return;
  }

  if (action === "delete-project") {
    if (!state.projects.length) throw new Error("No projects loaded. Expand a field first.");
    const defaultProjectId = state.selectedProjectId || state.projects[0].id;
    openDialog(
      "Delete Project",
      [{ name: "project_id", label: "Project", type: "select", required: true, value: defaultProjectId, options: projectOptions() }],
      async (values) => deleteProject(values.project_id),
    );
    return;
  }

  if (action === "navigate-up-folder") {
    const projectId = ensureSelectedProject();
    if (!state.currentPath) {
      showToast("Already at root folder");
      return;
    }
    const idx = state.currentPath.lastIndexOf("/");
    const parentPath = idx >= 0 ? state.currentPath.slice(0, idx) : "";
    await browseFiles(projectId, parentPath);
    return;
  }

  if (action === "commit-files") {
    openDialog(
      "Files At Commit",
      [{ name: "commit_id", label: "Commit ID", required: true, type: "number" }],
      async (values) => filesAtCommit(values.commit_id),
    );
    return;
  }

  if (action === "upload-commit") {
    const projectId = ensureSelectedProject();
    zipFileInput.value = "";
    zipFileInput.click();
    zipFileInput.onchange = () => {
      if (!zipFileInput.files?.[0]) return;
      openDialog(
        "Upload Commit ZIP",
        [
          { name: "project_id", label: "Project ID", required: true, value: projectId },
          { name: "message", label: "Commit Message" },
        ],
        async (values) => uploadCommit(values.project_id, values.message),
      );
    };
    return;
  }

  if (action === "export-selected-version") {
    const commitId = ensureSelectedVersionCommit();
    await downloadCommit(commitId);
    return;
  }
}

for (const button of document.querySelectorAll("[data-action]")) {
  button.addEventListener("click", async () => {
    const action = button.dataset.action;
    try {
      await handleAction(action);
    } catch (error) {
      showToast(error.message, true);
      log(error.message, "Error");
    }
  });
}

setSelected("", "");
renderTree();
renderFiles();
renderFileVersions();
renderCommitVersions();
log("Ready");

listFields(true).catch((error) => {
  showToast(error.message, true);
  log(error.message, "Error");
});
