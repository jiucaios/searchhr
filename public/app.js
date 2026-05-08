const form = document.querySelector("#profileForm");
const submitBtn = document.querySelector("#submitBtn");
const clearBtn = document.querySelector("#clearBtn");
const statusPill = document.querySelector("#statusPill");
const overviewPanel = document.querySelector("#overviewPanel");
const jsonPanel = document.querySelector("#jsonPanel");
const evidencePanel = document.querySelector("#evidencePanel");
const tabs = document.querySelectorAll(".tab");

const emptyText = "等待生成公司画像";

function setStatus(text, className = "") {
  statusPill.textContent = text;
  statusPill.className = `status-pill ${className}`.trim();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function listValue(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return '<span class="muted">暂无证据</span>';
  }
  return `<div class="chips">${items.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("")}</div>`;
}

function textValue(value) {
  return escapeHtml(value || "暂无证据");
}

function field(title, value, wide = false, isList = false) {
  return `
    <div class="field ${wide ? "wide" : ""}">
      <div class="field-title">${escapeHtml(title)}</div>
      <div class="field-value">${isList ? listValue(value) : textValue(value)}</div>
    </div>
  `;
}

function localizeStatus(value) {
  const statusMap = {
    success: "生成成功",
    failed: "生成失败",
    pending: "处理中",
  };
  return statusMap[value] || value;
}

function localizeMissingInfo(items) {
  const fieldMap = {
    industry: "所属行业",
    business: "主营业务",
    business_model: "商业模式",
    company_stage: "公司阶段",
    company_size: "公司规模",
    main_products: "核心产品",
    products: "核心产品",
    tech_stack: "技术栈",
    hiring_positions: "招聘岗位",
    hiring_roles: "招聘岗位",
    candidate_preferences: "候选人偏好",
    risk_signals: "风险信号",
    website: "官网",
    company_website: "官网",
  };
  if (!Array.isArray(items)) {
    return [];
  }
  return items.map((item) => fieldMap[item] || item);
}

function renderOverview(payload) {
  if (!payload) {
    overviewPanel.innerHTML = `<div class="empty-state">${emptyText}</div>`;
    return;
  }

  if (payload.status === "failed") {
    overviewPanel.innerHTML = `
      <div class="overview-grid">
        ${field("状态", localizeStatus(payload.status))}
        ${field("失败原因", payload.reason || "未找到有效公司信息")}
        ${field("缺失信息", localizeMissingInfo(payload.missing_info || []), true, true)}
      </div>
    `;
    return;
  }

  const profile = payload.company_profile || {};
  overviewPanel.innerHTML = `
    <div class="overview-grid">
      ${field("状态", localizeStatus(payload.status))}
      ${field("公司名称", profile.company_name)}
      ${field("官网", profile.website)}
      ${field("行业", profile.industry)}
      ${field("商业模式", profile.business_model)}
      ${field("公司阶段", profile.company_stage)}
      ${field("公司规模", profile.company_size)}
      ${field("主营业务", profile.business, true)}
      ${field("核心产品", profile.main_products, false, true)}
      ${field("技术栈", profile.tech_stack, false, true)}
      ${field("招聘岗位", profile.hiring_positions, false, true)}
      ${field("候选人偏好", profile.candidate_preferences, true, true)}
      ${field("风险信号", profile.risk_signals, true, true)}
      ${field("缺失信息", localizeMissingInfo(profile.missing_info), true, true)}
      ${field("画像总结", profile.summary, true)}
    </div>
  `;
}

function renderEvidence(evidence) {
  if (!Array.isArray(evidence) || evidence.length === 0) {
    evidencePanel.innerHTML = '<div class="empty-state">暂无证据来源</div>';
    return;
  }

  evidencePanel.innerHTML = evidence
    .map((item) => {
      const url = item.url || "";
      return `
        <article class="evidence-item">
          <div class="evidence-source">${escapeHtml(item.source || "搜索结果")}</div>
          ${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(url)}</a>` : ""}
          <p>${escapeHtml(item.content || "")}</p>
        </article>
      `;
    })
    .join("");
}

function renderPayload(payload) {
  renderOverview(payload);
  jsonPanel.textContent = payload ? JSON.stringify(payload, null, 2) : "";
  renderEvidence(payload?.raw_evidence || []);
}

function activateTab(tabName) {
  tabs.forEach((item) => item.classList.toggle("active", item.dataset.tab === tabName));
  document.querySelectorAll(".panel").forEach((item) => {
    item.classList.toggle("active", item.id === `${tabName}Panel`);
  });
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    activateTab(tab.dataset.tab);
  });
});

clearBtn.addEventListener("click", () => {
  renderPayload(null);
  activateTab("overview");
  setStatus("待生成");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(form);
  const payload = {
    company_name: formData.get("company_name"),
    company_website: formData.get("company_website"),
    job_description: formData.get("job_description"),
    max_iterations: Number(formData.get("max_iterations") || 1),
  };

  submitBtn.disabled = true;
  setStatus("检索中", "loading");
  renderPayload({
    status: "处理中",
    company_profile: {
      company_name: payload.company_name,
      website: payload.company_website,
      summary: "正在搜索官网、招聘、技术栈、融资新闻和风险信号...",
      missing_info: [],
    },
    raw_evidence: [],
  });

  try {
    const response = await fetch("/api/company-profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    renderPayload(result);
    setStatus(result.status === "success" ? "生成成功" : "生成失败", result.status === "success" ? "success" : "failed");
  } catch (error) {
    const failed = {
      status: "failed",
      reason: error.message,
      missing_info: ["接口响应"],
    };
    renderPayload(failed);
    setStatus("生成失败", "failed");
  } finally {
    submitBtn.disabled = false;
  }
});

renderPayload(null);
