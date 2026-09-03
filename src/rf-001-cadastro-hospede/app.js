// =====================================================================
// Aplicação Cliente: Grand Plaza Hotel Management (RF-001)
// Orquestrador de Estados, Validações e Persistência Dual (API / LocalStorage)
// =====================================================================

const API_BASE_URL = "/api/v1";

const STORAGE_KEY = "grand_plaza_hospedes_db";

// Dados iniciais padrão (Seeds locais para demonstração imediata)
const DEFAULT_SEEDS = [
  {
    uuid_publico: "c4a1e944-938b-4c28-97f4-8d4cb28d2001",
    nome: "Carlos Eduardo Mendes",
    email: "carlos.mendes@email.com",
    cpf: "12345678901",
    telefone: "(11) 98765-4321",
    data_nascimento: "1985-04-12",
    observacoes: "Prefere quartos em andares altos."
  },
  {
    uuid_publico: "d5b2f055-049c-5d39-08a5-9e5dc39e3002",
    nome: "Mariana Alencar Santos",
    email: "mariana.alencar@email.com",
    cpf: "98765432100",
    telefone: "(21) 99887-7665",
    data_nascimento: "1992-09-28",
    observacoes: "Hóspede corporativa VIP."
  }
];

// Validação Algorítmica Módulo 11 do CPF
function validarCPF(cpf) {
  const limpo = cpf.replace(/\D/g, "");
  if (limpo.length !== 11 || /^(\d)\1{10}$/.test(limpo)) return false;

  let soma = 0;
  for (let i = 0; i < 9; i++) soma += parseInt(limpo.charAt(i)) * (10 - i);
  let resto = (soma * 10) % 11;
  if (resto === 10 || resto === 11) resto = 0;
  if (resto !== parseInt(limpo.charAt(9))) return false;

  soma = 0;
  for (let i = 0; i < 10; i++) soma += parseInt(limpo.charAt(i)) * (11 - i);
  resto = (soma * 10) % 11;
  if (resto === 10 || resto === 11) resto = 0;
  return resto === parseInt(limpo.charAt(10));
}

// Máscaras de Entrada Dinâmicas
function formatarCPF(v) {
  v = v.replace(/\D/g, "").slice(0, 11);
  if (v.length > 9) return v.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, "$1.$2.$3-$4");
  if (v.length > 6) return v.replace(/(\d{3})(\d{3})(\d{1,3})/, "$1.$2.$3");
  if (v.length > 3) return v.replace(/(\d{3})(\d{1,3})/, "$1.$2");
  return v;
}

function formatarTelefone(v) {
  v = v.replace(/\D/g, "").slice(0, 11);
  if (v.length > 10) return v.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
  if (v.length > 6) return v.replace(/^(\d{2})(\d{4})(\d{0,4})$/, "($1) $2-$3");
  if (v.length > 2) return v.replace(/^(\d{2})(\d{0,5})$/, "($1) $2");
  return v;
}

// Repositório de Hóspedes (Abstração com Fallback Inteligente)
class HospedeRepository {
  static getLocalData() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_SEEDS));
      return DEFAULT_SEEDS;
    }
    try {
      return JSON.parse(raw);
    } catch {
      return DEFAULT_SEEDS;
    }
  }

  static async listar() {
    try {
      const resp = await fetch(`${API_BASE_URL}/hospedes`, { method: "GET" });
      if (resp.ok) {
        const json = await resp.json();
        return json.data;
      }
    } catch (e) {
      console.warn("Aguardando inicialização do backend API...", e);
    }
    return this.getLocalData();
  }

  static async salvar(hospede) {
    try {
      // 1. Tenta persistir na API REST FastAPI
      const resp = await fetch(`${API_BASE_URL}/hospedes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: hospede.nome,
          email: hospede.email,
          cpf: hospede.cpf.replace(/\D/g, ""),
          telefone: hospede.telefone,
          data_nascimento: hospede.dataNascimento,
          observacoes: hospede.observacoes || null
        })
      });

      if (resp.status === 409) {
        const err = await resp.json();
        throw new Error(err.detail?.message || "E-mail ou CPF já cadastrado no sistema.");
      }

      if (resp.ok) {
        const json = await resp.json();
        return json.data;
      }
    } catch (err) {
      // Se for erro de duplicidade (409), propaga imediatamente para o formulário
      if (err.message && (err.message.includes("cadastrado") || err.message.includes("registrado"))) {
        throw err;
      }
      console.warn("Salvando em LocalStorage com simulação de latência de rede...", err);
    }

    // 2. Fallback Seguro para LocalStorage (com delay simulado de 600ms para exibir spinner)
    await new Promise((resolve) => setTimeout(resolve, 600));
    const lista = this.getLocalData();

    // Verificação de unicidade local (RN-01 e RN-02)
    const cpfLimpo = hospede.cpf.replace(/\D/g, "");
    if (lista.some((h) => h.email.toLowerCase() === hospede.email.toLowerCase())) {
      throw new Error("Este endereço de e-mail já está cadastrado no sistema.");
    }
    if (lista.some((h) => h.cpf.replace(/\D/g, "") === cpfLimpo)) {
      throw new Error("Este CPF já se encontra registrado no banco de hóspedes.");
    }

    const novo = {
      uuid_publico: "loc-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 6),
      nome: hospede.nome,
      email: hospede.email,
      cpf: cpfLimpo,
      telefone: hospede.telefone,
      data_nascimento: hospede.dataNascimento,
      observacoes: hospede.observacoes || null,
      created_at: new Date().toISOString()
    };

    lista.unshift(novo);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lista));
    return novo;
  }
}

// Inicialização da UI e Manipulação de Eventos
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("formHospede");
  const btnSalvar = document.getElementById("btnSalvar");
  const btnText = document.getElementById("btnText");
  const btnLimpar = document.getElementById("btnLimpar");
  const errorBanner = document.getElementById("errorBanner");
  const errorMessage = document.getElementById("errorMessage");
  const successPanel = document.getElementById("successPanel");
  const successDetails = document.getElementById("successDetails");
  const listaHospedesBody = document.getElementById("listaHospedesBody");
  const btnResetarDemo = document.getElementById("btnResetarDemo");

  const inputNome = document.getElementById("nome");
  const inputEmail = document.getElementById("email");
  const inputCpf = document.getElementById("cpf");
  const inputTelefone = document.getElementById("telefone");
  const inputDataNascimento = document.getElementById("dataNascimento");

  // Máscaras de digitação
  inputCpf.addEventListener("input", (e) => (e.target.value = formatarCPF(e.target.value)));
  inputTelefone.addEventListener("input", (e) => (e.target.value = formatarTelefone(e.target.value)));

  // Funções de Renderização dos Estados
  function setFieldError(fieldId, isError) {
    const wrap = document.getElementById(`wrap-${fieldId}`);
    if (wrap) {
      if (isError) {
        wrap.classList.add("is-invalid");
        wrap.classList.remove("is-valid");
      } else {
        wrap.classList.remove("is-invalid");
        wrap.classList.add("is-valid");
      }
    }
  }

  function showGlobalError(msg) {
    errorMessage.textContent = msg;
    errorBanner.classList.add("is-active");
    successPanel.classList.remove("is-active");
  }

  function clearErrors() {
    errorBanner.classList.remove("is-active");
    ["nome", "email", "cpf", "telefone", "dataNascimento"].forEach((f) => {
      const wrap = document.getElementById(`wrap-${f}`);
      if (wrap) wrap.classList.remove("is-invalid");
    });
  }

  function setLoading(loading) {
    btnSalvar.disabled = loading;
    if (loading) {
      btnText.innerHTML = `<span class="spinner"></span> Gravando hóspede...`;
      clearErrors();
      successPanel.classList.remove("is-active");
    } else {
      btnText.textContent = "Confirmar Cadastro de Hóspede";
    }
  }

  function escaparHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }

  async function atualizarTabela() {
    const hospedes = await HospedeRepository.listar();
    if (!hospedes || hospedes.length === 0) {
      listaHospedesBody.innerHTML = `<tr><td colspan="4" class="empty-state">Nenhum hóspede cadastrado ainda.</td></tr>`;
      return;
    }

    listaHospedesBody.innerHTML = hospedes
      .map(
        (h) => `
      <tr>
        <td><strong>${escaparHTML(h.nome)}</strong></td>
        <td>${escaparHTML(h.email)}</td>
        <td><code>${escaparHTML(formatarCPF(h.cpf))}</code></td>
        <td><span class="tag-badge">Ativo</span></td>
      </tr>
    `
      )
      .join("");
  }

  // Submissão do Formulário
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearErrors();

    const dados = {
      nome: inputNome.value.trim(),
      email: inputEmail.value.trim(),
      cpf: inputCpf.value.trim(),
      telefone: inputTelefone.value.trim(),
      dataNascimento: inputDataNascimento.value,
      observacoes: document.getElementById("observacoes").value.trim()
    };

    // Validações Locais
    let temErro = false;

    if (dados.nome.length < 3) {
      setFieldError("nome", true);
      temErro = true;
    } else {
      setFieldError("nome", false);
    }

    if (!dados.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(dados.email)) {
      setFieldError("email", true);
      temErro = true;
    } else {
      setFieldError("email", false);
    }

    if (!validarCPF(dados.cpf)) {
      setFieldError("cpf", true);
      temErro = true;
    } else {
      setFieldError("cpf", false);
    }

    if (dados.telefone.replace(/\D/g, "").length < 10) {
      setFieldError("telefone", true);
      temErro = true;
    } else {
      setFieldError("telefone", false);
    }

    if (!dados.dataNascimento || new Date(dados.dataNascimento) > new Date()) {
      setFieldError("dataNascimento", true);
      temErro = true;
    } else {
      setFieldError("dataNascimento", false);
    }

    if (temErro) {
      showGlobalError("Por favor, corrija os campos destacados em vermelho antes de prosseguir.");
      return;
    }

    // Processamento de Persistência com Estado de Loading
    setLoading(true);

    try {
      const salvo = await HospedeRepository.salvar(dados);

      // Estado de Sucesso
      successDetails.innerHTML = `
        <strong>Hóspede:</strong> ${salvo.nome}<br>
        <strong>E-mail:</strong> ${salvo.email}<br>
        <strong>Identificador Único (UUID):</strong> <code>${salvo.uuid_publico}</code>
      `;
      successPanel.classList.add("is-active");

      form.reset();
      ["nome", "email", "cpf", "telefone", "dataNascimento"].forEach((f) => {
        const wrap = document.getElementById(`wrap-${f}`);
        if (wrap) wrap.classList.remove("is-valid");
      });

      await atualizarTabela();
    } catch (err) {
      showGlobalError(err.message || "Falha ao gravar os dados do hóspede.");
      if (err.message.includes("e-mail")) setFieldError("email", true);
      if (err.message.includes("CPF")) setFieldError("cpf", true);
    } finally {
      setLoading(false);
    }
  });

  btnLimpar.addEventListener("click", () => {
    form.reset();
    clearErrors();
    successPanel.classList.remove("is-active");
  });

  btnResetarDemo.addEventListener("click", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_SEEDS));
    await atualizarTabela();
  });

  // Carregamento inicial da listagem
  atualizarTabela();
});
