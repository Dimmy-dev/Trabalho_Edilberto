/**
 * GRAND PLAZA HOTEL MANAGEMENT SYSTEM — CORE SPA UNIFICADO
 * Motor de Simulação Relacional LocalStorage (Client-Side Storage Engine)
 * Disciplina: Laboratório de Inovação III — Prof. Edilberto Silva
 * Autor: Dimitri Lopes Barreto
 */

(function () {
  'use strict';

  // =========================================================================
  // 1. UTILITÁRIOS E FUNÇÕES AUXILIARES
  // =========================================================================

  function gerarUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function formatarMoeda(valor) {
    const num = Number(valor) || 0;
    return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function formatarDataHora(isoString) {
    if (!isoString) return '-';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('pt-BR') + ' às ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  }

  function formatarData(isoString) {
    if (!isoString) return '-';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('pt-BR');
    } catch {
      return isoString;
    }
  }

  function formatarCPF(cpf) {
    const limpo = (cpf || '').replace(/\D/g, '');
    if (limpo.length !== 11) return cpf;
    return limpo.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
  }

  // Validador oficial de CPF (Algoritmo Módulo 11)
  function validarCPF(cpf) {
    const limpo = (cpf || '').replace(/\D/g, '');
    if (limpo.length !== 11) return false;
    if (/^(\d)\1{10}$/.test(limpo)) return false;

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

  function showToast(mensagem, tipo = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${tipo}`;
    toast.textContent = mensagem;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(8px)';
      setTimeout(() => toast.remove(), 300);
    }, 3800);
  }

  // =========================================================================
  // 2. MOTOR DE BANCO DE DADOS EM LOCALSTORAGE (SIMULATED STORAGE ENGINE)
  // =========================================================================

  const DB_PREFIX = 'gp_hotel_db_';

  const LocalStorageDB = {
    carregar(tabela) {
      try {
        const item = localStorage.getItem(DB_PREFIX + tabela);
        return item ? JSON.parse(item) : [];
      } catch (e) {
        console.error('Falha ao ler tabela:', tabela, e);
        return [];
      }
    },

    salvar(tabela, dados) {
      try {
        localStorage.setItem(DB_PREFIX + tabela, JSON.stringify(dados));
      } catch (e) {
        console.error('Falha ao gravar tabela:', tabela, e);
      }
    },

    // Auto-seed inicial de demonstração
    inicializar(forcarReset = false) {
      const jaInicializado = localStorage.getItem('gp_db_seeded');
      if (jaInicializado && !forcarReset) return;

      console.info('[LocalStorageDB] Populando dados iniciais de demonstração...');

      // 1. Operadores (RF-003)
      const operadores = [
        {
          id: 1,
          uuid_operador: 'op-001-admin',
          nome: 'Administrador Master',
          email: 'admin@grandplaza.com',
          cargo: 'ADMIN',
          ativo: true,
          criado_em: '2026-01-10T08:00:00'
        },
        {
          id: 2,
          uuid_operador: 'op-002-gerente',
          nome: 'Carlos Alberto (Gerência Geral)',
          email: 'gerencia@grandplaza.com',
          cargo: 'GERENTE',
          ativo: true,
          criado_em: '2026-01-12T09:00:00'
        },
        {
          id: 3,
          uuid_operador: 'op-003-recepcao',
          nome: 'Maria Oliveira (Recepção Central)',
          email: 'recepcao@grandplaza.com',
          cargo: 'RECEPCIONISTA',
          ativo: true,
          criado_em: '2026-01-15T07:30:00'
        }
      ];

      // 2. Acomodações do Rack (RF-004)
      const acomodacoes = [
        { uuid_quarto: 'q-101', numero: '101', andar: 1, categoria: 'STANDARD', capacidade: 2, preco_diaria: 180.0, status: 'DISPONIVEL', caracteristicas: 'Cama Queen, Ar Split, Wi-Fi 5G, Smart TV 43' },
        { uuid_quarto: 'q-102', numero: '102', andar: 1, categoria: 'STANDARD', capacidade: 2, preco_diaria: 180.0, status: 'OCUPADO', caracteristicas: 'Cama Queen, Frigobar, Vista Interna' },
        { uuid_quarto: 'q-103', numero: '103', andar: 1, categoria: 'STANDARD', capacidade: 2, preco_diaria: 180.0, status: 'LIMPEZA', caracteristicas: 'Cama Casal, Mesa de Trabalho, Wi-Fi' },
        { uuid_quarto: 'q-104', numero: '104', andar: 1, categoria: 'LUXO', capacidade: 3, preco_diaria: 280.0, status: 'DISPONIVEL', caracteristicas: 'Cama King, Banheira de Hidro, Varanda' },
        { uuid_quarto: 'q-105', numero: '105', andar: 1, categoria: 'LUXO', capacidade: 3, preco_diaria: 280.0, status: 'DISPONIVEL', caracteristicas: 'Cama King + Solteiro, Varanda Frente' },
        { uuid_quarto: 'q-201', numero: '201', andar: 2, categoria: 'LUXO', capacidade: 3, preco_diaria: 320.0, status: 'DISPONIVEL', caracteristicas: 'Cama King, Cafeteira Nespresso, Vista Jardim' },
        { uuid_quarto: 'q-202', numero: '202', andar: 2, categoria: 'SUITE_PRESIDENCIAL', capacidade: 4, preco_diaria: 550.0, status: 'OCUPADO', caracteristicas: '2 Ambientes, Jacuzzi Panorâmica, Closet' },
        { uuid_quarto: 'q-203', numero: '203', andar: 2, categoria: 'STANDARD', capacidade: 2, preco_diaria: 190.0, status: 'MANUTENCAO', caracteristicas: 'Cama Queen (Revisão de Ar Condicionado)' },
        { uuid_quarto: 'q-204', numero: '204', andar: 2, categoria: 'LUXO', capacidade: 3, preco_diaria: 300.0, status: 'DISPONIVEL', caracteristicas: 'Cama King, Sacada Ampla, Ducha Dupla' },
        { uuid_quarto: 'q-205', numero: '205', andar: 2, categoria: 'SUITE_PRESIDENCIAL', capacidade: 4, preco_diaria: 600.0, status: 'DISPONIVEL', caracteristicas: 'Andar VIP, Serviço de Mordomo, Vista Panorâmica' }
      ];

      // 3. Hóspedes (RF-001 & RF-002)
      const hospedes = [
        {
          uuid_hospede: 'hosp-001',
          nome: 'João Santos Silva',
          cpf: '12345678909',
          email: 'joao.santos@email.com',
          telefone: '11988887777',
          data_nascimento: '1988-04-15',
          endereco: 'Av. Paulista, 1500, Apto 82',
          cidade: 'São Paulo',
          estado: 'SP',
          pais: 'Brasil',
          ativo: true,
          criado_em: '2026-02-01T10:00:00'
        },
        {
          uuid_hospede: 'hosp-002',
          nome: 'Dra. Beatriz de Souza Lima',
          cpf: '98765432100',
          email: 'beatriz.lima@hospital.med.br',
          telefone: '21977776666',
          data_nascimento: '1985-09-22',
          endereco: 'Rua Barata Ribeiro, 450',
          cidade: 'Rio de Janeiro',
          estado: 'RJ',
          pais: 'Brasil',
          ativo: true,
          criado_em: '2026-02-10T14:30:00'
        },
        {
          uuid_hospede: 'hosp-003',
          nome: 'Roberto Carlos Braga',
          cpf: '11144477735',
          email: 'roberto.braga@musica.com.br',
          telefone: '31966665555',
          data_nascimento: '1975-11-30',
          endereco: 'Rua da Bahia, 1200',
          cidade: 'Belo Horizonte',
          estado: 'MG',
          pais: 'Brasil',
          ativo: true,
          criado_em: '2026-03-01T09:15:00'
        }
      ];

      // 4. Catálogo de Frigobar e Serviços (RF-005)
      const catalogo = [
        { uuid_item: 'item-001', codigo: 'FRIG-001', nome: 'Água Mineral sem Gás 500ml', categoria: 'FRIGOBAR', preco_unitario: 6.0, descricao: 'Água da fonte em garrafa mineral' },
        { uuid_item: 'item-002', codigo: 'FRIG-002', nome: 'Refrigerante Coca-Cola Lata 350ml', categoria: 'FRIGOBAR', preco_unitario: 9.0, descricao: 'Lata refrigerada' },
        { uuid_item: 'item-003', codigo: 'FRIG-003', nome: 'Cerveja Artesanal IPA 355ml', categoria: 'FRIGOBAR', preco_unitario: 18.0, descricao: 'Cerveja premium com lúpulo aromático' },
        { uuid_item: 'item-004', codigo: 'FRIG-004', nome: 'Barra de Chocolate Importado 100g', categoria: 'FRIGOBAR', preco_unitario: 14.0, descricao: 'Chocolate suíço 70% cacau' },
        { uuid_item: 'item-005', codigo: 'FRIG-005', nome: 'Castanha de Caju Selecionada 80g', categoria: 'FRIGOBAR', preco_unitario: 12.0, descricao: 'Castanhas torradas e levemente salgadas' },
        { uuid_item: 'item-006', codigo: 'SERV-001', nome: 'Café da Manhã no Quarto (Continental)', categoria: 'SERVICO_QUARTO', preco_unitario: 45.0, descricao: 'Cesta de pães artesanais, suco natural, frutas e café' },
        { uuid_item: 'item-007', codigo: 'SERV-002', nome: 'Lavanderia Express (Camisa Social)', categoria: 'LAVANDERIA', preco_unitario: 25.0, descricao: 'Lavagem delicada e passadoria a vapor' }
      ];

      // 5. Hospedagens Ativas Pré-configuradas (RF-004)
      const dataOntem = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
      const dataAmanha = new Date(Date.now() + 24 * 3600 * 1000).toISOString();

      const hospedagens = [
        {
          uuid_hospedagem: 'hosped-102-ativa',
          uuid_hospede: 'hosp-001',
          uuid_quarto: 'q-102',
          data_checkin: dataOntem,
          previsao_checkout: dataAmanha,
          data_checkout: null,
          tarifa_diaria_aplicada: 180.0,
          total_diarias: 180.0,
          total_consumo: 24.0,
          total_geral: 204.0,
          status: 'ATIVA',
          acompanhantes: 'Marcos Silva',
          observacoes: 'Quarto silencioso preferencial'
        },
        {
          uuid_hospedagem: 'hosped-202-ativa',
          uuid_hospede: 'hosp-002',
          uuid_quarto: 'q-202',
          data_checkin: dataOntem,
          previsao_checkout: dataAmanha,
          data_checkout: null,
          tarifa_diaria_aplicada: 550.0,
          total_diarias: 550.0,
          total_consumo: 63.0,
          total_geral: 613.0,
          status: 'ATIVA',
          acompanhantes: '',
          observacoes: 'Check-in VIP'
        }
      ];

      // 6. Consumos Ativos (RF-005)
      const consumos = [
        {
          uuid_consumo: 'cons-001',
          uuid_hospedagem: 'hosped-102-ativa',
          uuid_item: 'item-001',
          nome_item: 'Água Mineral sem Gás 500ml',
          quantidade: 2,
          preco_unitario: 6.0,
          subtotal: 12.0,
          status: 'REGISTRADO',
          criado_em: dataOntem,
          motivo_estorno: null
        },
        {
          uuid_consumo: 'cons-002',
          uuid_hospedagem: 'hosped-102-ativa',
          uuid_item: 'item-005',
          nome_item: 'Castanha de Caju Selecionada 80g',
          quantidade: 1,
          preco_unitario: 12.0,
          subtotal: 12.0,
          status: 'REGISTRADO',
          criado_em: dataOntem,
          motivo_estorno: null
        },
        {
          uuid_consumo: 'cons-003',
          uuid_hospedagem: 'hosped-202-ativa',
          uuid_item: 'item-006',
          nome_item: 'Café da Manhã no Quarto (Continental)',
          quantidade: 1,
          preco_unitario: 45.0,
          subtotal: 45.0,
          status: 'REGISTRADO',
          criado_em: dataOntem,
          motivo_estorno: null
        },
        {
          uuid_consumo: 'cons-004',
          uuid_hospedagem: 'hosped-202-ativa',
          uuid_item: 'item-003',
          nome_item: 'Cerveja Artesanal IPA 355ml',
          quantidade: 1,
          preco_unitario: 18.0,
          subtotal: 18.0,
          status: 'REGISTRADO',
          criado_em: dataOntem,
          motivo_estorno: null
        }
      ];

      // 7. Ordens de Serviço (RF-006)
      const ordensServico = [
        {
          uuid_os: 'os-001',
          codigo_os: 'OS-2026-0001',
          quarto_numero: '103',
          tipo: 'LIMPEZA',
          prioridade: 'ALTA',
          status: 'PENDENTE',
          descricao: 'Higienização completa pós-checkout (Rouparia, toalhas e desinfecção)',
          responsavel: 'Camareira Ana Lúcia',
          criado_em: dataOntem,
          concluido_em: null
        },
        {
          uuid_os: 'os-002',
          codigo_os: 'OS-2026-0002',
          quarto_numero: '203',
          tipo: 'MANUTENCAO',
          prioridade: 'ALTA',
          status: 'EM_EXECUCAO',
          descricao: 'Revisão técnica de ar-condicionado e recarga de gás refrigerante',
          responsavel: 'Técnico Carlos Eletricista',
          criado_em: dataOntem,
          concluido_em: null
        }
      ];

      this.salvar('operadores', operadores);
      this.salvar('acomodacoes', acomodacoes);
      this.salvar('hospedes', hospedes);
      this.salvar('catalogo', catalogo);
      this.salvar('hospedagens', hospedagens);
      this.salvar('consumos', consumos);
      this.salvar('ordens_servico', ordensServico);
      localStorage.setItem('gp_db_seeded', 'true');

      // Login inicial simulado com a Recepcionista para já abrir o dashboard pronto
      if (!localStorage.getItem('gp_operador_logado')) {
        localStorage.setItem('gp_operador_logado', JSON.stringify(operadores[2]));
      }

      console.info('[LocalStorageDB] Inicialização concluída com sucesso.');
    }
  };

  // Garante inicialização prévia
  LocalStorageDB.inicializar();

  // =========================================================================
  // 3. CAMADA DE SERVIÇOS (API EMULADA / CONTROLLERS)
  // =========================================================================

  const API = {
    // AUTH (RF-003)
    auth: {
      async login(email, senha) {
        const operadores = LocalStorageDB.carregar('operadores');
        const op = operadores.find(o => o.email.toLowerCase() === (email || '').trim().toLowerCase());
        if (!op) {
          throw new Error('E-mail não encontrado no sistema.');
        }
        if (!op.ativo) {
          throw new Error('Operador inativado. Acesso negado.');
        }
        // Senha padrão aceita na demonstração
        localStorage.setItem('gp_operador_logado', JSON.stringify(op));
        return { success: true, data: { operador: op, token: 'mock-jwt-token-' + op.uuid_operador }, error: null };
      },
      async logout() {
        localStorage.removeItem('gp_operador_logado');
        return { success: true, data: null, error: null };
      },
      async me() {
        const opStr = localStorage.getItem('gp_operador_logado');
        if (!opStr) throw new Error('Não autenticado.');
        return { success: true, data: JSON.parse(opStr), error: null };
      }
    },

    // ACOMODAÇÕES E RACK (RF-004)
    acomodacoes: {
      async listar(filtroCategoria = 'TODAS') {
        let quartos = LocalStorageDB.carregar('acomodacoes');
        if (filtroCategoria && filtroCategoria !== 'TODAS') {
          quartos = quartos.filter(q => q.categoria === filtroCategoria);
        }
        const hospedagens = LocalStorageDB.carregar('hospedagens');
        const hospedes = LocalStorageDB.carregar('hospedes');

        // Enriquece os quartos ocupados com nome do hóspede e estadia
        const resultado = quartos.map(q => {
          const copia = { ...q };
          if (q.status === 'OCUPADO') {
            const estadia = hospedagens.find(h => h.uuid_quarto === q.uuid_quarto && h.status === 'ATIVA');
            if (estadia) {
              const hosp = hospedes.find(hp => hp.uuid_hospede === estadia.uuid_hospede);
              copia.hospede_nome = hosp ? hosp.nome : 'Hóspede Registrado';
              copia.uuid_hospedagem_ativa = estadia.uuid_hospedagem;
              copia.data_checkin = estadia.data_checkin;
            }
          }
          return copia;
        });

        return { success: true, data: resultado, error: null };
      },

      async alterarStatus(uuidQuarto, novoStatus) {
        const quartos = LocalStorageDB.carregar('acomodacoes');
        const quarto = quartos.find(q => q.uuid_quarto === uuidQuarto);
        if (!quarto) throw new Error('Quarto não encontrado.');

        // Validação de transição de estado da máquina hoteleira
        if (quarto.status === 'OCUPADO' && novoStatus !== 'OCUPADO') {
          throw new Error('Não é possível alterar o status de um quarto OCUPADO diretamente. Realize o Check-out.');
        }

        quarto.status = novoStatus;
        LocalStorageDB.salvar('acomodacoes', quartos);
        return { success: true, data: quarto, error: null };
      }
    },

    // HÓSPEDES (RF-001 & RF-002)
    hospedes: {
      async listar(termo = '') {
        let hospedes = LocalStorageDB.carregar('hospedes');
        if (termo) {
          const t = termo.toLowerCase().trim();
          hospedes = hospedes.filter(h =>
            (h.nome && h.nome.toLowerCase().includes(t)) ||
            (h.cpf && h.cpf.includes(t)) ||
            (h.email && h.email.toLowerCase().includes(t))
          );
        }
        return { success: true, data: hospedes, error: null };
      },

      async criar(dados) {
        const limpoCPF = (dados.cpf || '').replace(/\D/g, '');
        if (!validarCPF(limpoCPF)) {
          throw new Error('CPF inválido pelo algoritmo do Módulo 11.');
        }

        const hospedes = LocalStorageDB.carregar('hospedes');
        if (hospedes.some(h => (h.cpf || '').replace(/\D/g, '') === limpoCPF)) {
          throw new Error('Já existe um hóspede cadastrado com este CPF.');
        }

        const novo = {
          uuid_hospede: gerarUUID(),
          nome: dados.nome.trim(),
          cpf: limpoCPF,
          email: dados.email.trim(),
          telefone: (dados.telefone || '').trim(),
          data_nascimento: dados.data_nascimento || null,
          endereco: dados.endereco || '',
          cidade: dados.cidade || '',
          estado: dados.estado || '',
          pais: dados.pais || 'Brasil',
          ativo: true,
          criado_em: new Date().toISOString()
        };

        hospedes.unshift(novo);
        LocalStorageDB.salvar('hospedes', hospedes);
        return { success: true, data: novo, error: null };
      },

      async alterarStatus(uuidHospede, novoStatusAtivo) {
        const hospedes = LocalStorageDB.carregar('hospedes');
        const hosp = hospedes.find(h => h.uuid_hospede === uuidHospede);
        if (!hosp) throw new Error('Hóspede não encontrado.');

        hosp.ativo = Boolean(novoStatusAtivo);
        LocalStorageDB.salvar('hospedes', hospedes);
        return { success: true, data: hosp, error: null };
      }
    },

    // OPERADORES (RF-003)
    operadores: {
      async listar() {
        const operadores = LocalStorageDB.carregar('operadores');
        return { success: true, data: operadores, error: null };
      },

      async criar(dados) {
        const operadores = LocalStorageDB.carregar('operadores');
        if (operadores.some(o => o.email.toLowerCase() === dados.email.toLowerCase())) {
          throw new Error('E-mail institucional já cadastrado.');
        }

        const novo = {
          id: operadores.length + 1,
          uuid_operador: gerarUUID(),
          nome: dados.nome.trim(),
          email: dados.email.trim().toLowerCase(),
          cargo: dados.cargo || 'FUNCIONARIO',
          ativo: true,
          criado_em: new Date().toISOString()
        };

        operadores.push(novo);
        LocalStorageDB.salvar('operadores', operadores);
        return { success: true, data: novo, error: null };
      },

      async alterarStatus(uuidOperador, novoStatusAtivo) {
        const operadores = LocalStorageDB.carregar('operadores');
        const op = operadores.find(o => o.uuid_operador === uuidOperador);
        if (!op) throw new Error('Operador não encontrado.');

        op.ativo = Boolean(novoStatusAtivo);
        LocalStorageDB.salvar('operadores', operadores);
        return { success: true, data: op, error: null };
      }
    },

    // HOSPEDAGENS (RF-004)
    hospedagens: {
      async listarAtivas() {
        const hospedagens = LocalStorageDB.carregar('hospedagens');
        const ativas = hospedagens.filter(h => h.status === 'ATIVA');
        const hospedes = LocalStorageDB.carregar('hospedes');
        const quartos = LocalStorageDB.carregar('acomodacoes');

        const resultado = ativas.map(estadia => {
          const hosp = hospedes.find(hp => hp.uuid_hospede === estadia.uuid_hospede);
          const quarto = quartos.find(q => q.uuid_quarto === estadia.uuid_quarto);
          return {
            ...estadia,
            hospede_nome: hosp ? hosp.nome : 'Hóspede Desconhecido',
            hospede_cpf: hosp ? hosp.cpf : '',
            quarto_numero: quarto ? quarto.numero : '---',
            quarto_categoria: quarto ? quarto.categoria : 'STANDARD'
          };
        });

        return { success: true, data: resultado, error: null };
      },

      async checkin(dados) {
        const quartos = LocalStorageDB.carregar('acomodacoes');
        const quarto = quartos.find(q => q.uuid_quarto === dados.uuid_quarto);
        if (!quarto) throw new Error('Acomodação não encontrada.');
        if (quarto.status !== 'DISPONIVEL') {
          throw new Error(`O quarto ${quarto.numero} está ${quarto.status}. Apenas quartos DISPONÍVEIS podem receber check-in.`);
        }

        const hospedes = LocalStorageDB.carregar('hospedes');
        const hosp = hospedes.find(h => h.uuid_hospede === dados.uuid_hospede);
        if (!hosp) throw new Error('Hóspede não encontrado.');
        if (!hosp.ativo) throw new Error('Hóspede inativo no sistema.');

        const hospedagens = LocalStorageDB.carregar('hospedagens');
        const novaEstadia = {
          uuid_hospedagem: gerarUUID(),
          uuid_hospede: dados.uuid_hospede,
          uuid_quarto: dados.uuid_quarto,
          data_checkin: new Date().toISOString(),
          previsao_checkout: dados.previsao_saida || null,
          data_checkout: null,
          tarifa_diaria_aplicada: Number(quarto.preco_diaria) || 180.0,
          total_diarias: Number(quarto.preco_diaria) || 180.0,
          total_consumo: 0.0,
          total_geral: Number(quarto.preco_diaria) || 180.0,
          status: 'ATIVA',
          acompanhantes: dados.acompanhantes || '',
          observacoes: dados.observacoes || ''
        };

        // Transição de estado atômica do quarto: DISPONIVEL -> OCUPADO
        quarto.status = 'OCUPADO';

        hospedagens.unshift(novaEstadia);
        LocalStorageDB.salvar('acomodacoes', quartos);
        LocalStorageDB.salvar('hospedagens', hospedagens);

        return { success: true, data: novaEstadia, error: null };
      },

      async checkout(uuidHospedagem, formaPagamento = 'CARTAO_CREDITO', observacoes = '') {
        const hospedagens = LocalStorageDB.carregar('hospedagens');
        const estadia = hospedagens.find(h => h.uuid_hospedagem === uuidHospedagem);
        if (!estadia) throw new Error('Hospedagem não encontrada.');
        if (estadia.status !== 'ATIVA') throw new Error('Esta hospedagem já foi encerrada.');

        const quartos = LocalStorageDB.carregar('acomodacoes');
        const quarto = quartos.find(q => q.uuid_quarto === estadia.uuid_quarto);

        // Calcula total de consumo
        const consumos = LocalStorageDB.carregar('consumos');
        const consumosEstadia = consumos.filter(c => c.uuid_hospedagem === uuidHospedagem && c.status === 'REGISTRADO');
        const totalConsumo = consumosEstadia.reduce((acc, cur) => acc + (Number(cur.subtotal) || 0), 0);

        // Cálculo de diárias (mínimo 1 diária)
        const entrada = new Date(estadia.data_checkin);
        const agora = new Date();
        const diffHoras = Math.abs(agora - entrada) / 36e5;
        const numDiarias = Math.max(1, Math.ceil(diffHoras / 24));
        const totalDiarias = numDiarias * Number(estadia.tarifa_diaria_aplicada);

        const totalGeral = totalDiarias + totalConsumo;

        // Atualiza a hospedagem
        estadia.status = 'FINALIZADA';
        estadia.data_checkout = agora.toISOString();
        estadia.total_diarias = totalDiarias;
        estadia.total_consumo = totalConsumo;
        estadia.total_geral = totalGeral;
        estadia.forma_pagamento = formaPagamento;
        estadia.observacoes_checkout = observacoes;

        // Máquina de estados: Quarto passa obrigatoriamente para LIMPEZA
        if (quarto) {
          quarto.status = 'LIMPEZA';
          LocalStorageDB.salvar('acomodacoes', quartos);
        }

        LocalStorageDB.salvar('hospedagens', hospedagens);

        return {
          success: true,
          data: {
            uuid_hospedagem: estadia.uuid_hospedagem,
            total_diarias: totalDiarias,
            num_diarias: numDiarias,
            total_consumo: totalConsumo,
            valor_total: totalGeral,
            status_quarto: 'LIMPEZA'
          },
          error: null
        };
      }
    },

    // CATÁLOGO E CONSUMO (RF-005)
    consumo: {
      async listarCatalogo(categoria = 'TODAS') {
        let itens = LocalStorageDB.carregar('catalogo');
        if (categoria && categoria !== 'TODAS') {
          itens = itens.filter(i => i.categoria === categoria);
        }
        return { success: true, data: itens, error: null };
      },

      async lancar(dados) {
        const hospedagens = LocalStorageDB.carregar('hospedagens');
        const estadia = hospedagens.find(h => h.uuid_hospedagem === dados.uuid_hospedagem && h.status === 'ATIVA');
        if (!estadia) throw new Error('Estadia não encontrada ou já encerrada.');

        const catalogo = LocalStorageDB.carregar('catalogo');
        const item = catalogo.find(i => i.uuid_item === dados.uuid_item);
        if (!item) throw new Error('Item do catálogo não encontrado.');

        const qtd = parseInt(dados.quantidade) || 1;
        const subtotal = qtd * Number(item.preco_unitario);

        const consumos = LocalStorageDB.carregar('consumos');
        const novoConsumo = {
          uuid_consumo: gerarUUID(),
          uuid_hospedagem: dados.uuid_hospedagem,
          uuid_item: item.uuid_item,
          nome_item: item.nome,
          quantidade: qtd,
          preco_unitario: Number(item.preco_unitario),
          subtotal: subtotal,
          status: 'REGISTRADO',
          criado_em: new Date().toISOString(),
          motivo_estorno: null
        };

        consumos.unshift(novoConsumo);
        LocalStorageDB.salvar('consumos', consumos);

        return { success: true, data: novoConsumo, error: null };
      },

      async obterExtrato(uuidHospedagem) {
        const consumos = LocalStorageDB.carregar('consumos');
        const itensHosp = consumos.filter(c => c.uuid_hospedagem === uuidHospedagem);
        const total = itensHosp
          .filter(c => c.status === 'REGISTRADO')
          .reduce((acc, cur) => acc + Number(cur.subtotal), 0);

        return {
          success: true,
          data: {
            uuid_hospedagem: uuidHospedagem,
            itens: itensHosp,
            total_itens: itensHosp.length,
            valor_total_consumo: total
          },
          error: null
        };
      },

      async estornar(uuidConsumo, motivo = 'Cancelado a pedido do hóspede') {
        const consumos = LocalStorageDB.carregar('consumos');
        const cons = consumos.find(c => c.uuid_consumo === uuidConsumo);
        if (!cons) throw new Error('Consumo não encontrado.');
        if (cons.status === 'ESTORNADO') throw new Error('Este item já foi estornado.');

        cons.status = 'ESTORNADO';
        cons.motivo_estorno = motivo;
        LocalStorageDB.salvar('consumos', consumos);
        return { success: true, data: cons, error: null };
      }
    },

    // GOVERNANÇA E MANUTENÇÃO (RF-006)
    governanca: {
      async listar() {
        const ordens = LocalStorageDB.carregar('ordens_servico');
        return { success: true, data: ordens, error: null };
      },

      async criar(dados) {
        const ordens = LocalStorageDB.carregar('ordens_servico');
        const numSeq = ordens.length + 1;
        const nova = {
          uuid_os: gerarUUID(),
          codigo_os: `OS-2026-${String(numSeq).padStart(4, '0')}`,
          quarto_numero: (dados.quarto_numero || '').trim(),
          tipo: dados.tipo || 'LIMPEZA',
          prioridade: dados.prioridade || 'MEDIA',
          status: 'PENDENTE',
          descricao: (dados.descricao || '').trim(),
          responsavel: (dados.responsavel || 'Equipe de Governança').trim(),
          criado_em: new Date().toISOString(),
          concluido_em: null
        };
        ordens.unshift(nova);
        LocalStorageDB.salvar('ordens_servico', ordens);

        // Se o quarto existir no rack, atualiza o status de acordo
        const quartos = LocalStorageDB.carregar('acomodacoes');
        const q = quartos.find(x => x.numero === nova.quarto_numero);
        if (q && q.status !== 'OCUPADO') {
          q.status = nova.tipo === 'MANUTENCAO' ? 'MANUTENCAO' : 'LIMPEZA';
          LocalStorageDB.salvar('acomodacoes', quartos);
        }

        return { success: true, data: nova, error: null };
      },

      async concluir(uuidOs) {
        const ordens = LocalStorageDB.carregar('ordens_servico');
        const o = ordens.find(x => x.uuid_os === uuidOs);
        if (!o) throw new Error('Ordem de serviço não encontrada.');
        o.status = 'CONCLUIDA';
        o.concluido_em = new Date().toISOString();
        LocalStorageDB.salvar('ordens_servico', ordens);

        // Transição atômica: libera quarto para DISPONIVEL
        const quartos = LocalStorageDB.carregar('acomodacoes');
        const q = quartos.find(x => x.numero === o.quarto_numero);
        if (q && q.status !== 'OCUPADO') {
          q.status = 'DISPONIVEL';
          LocalStorageDB.salvar('acomodacoes', quartos);
        }

        return { success: true, data: o, error: null };
      }
    }
  };

  // =========================================================================
  // 4. CONTROLADORES DA INTERFACE (UI CONTROLLER)
  // =========================================================================

  let estadoApp = {
    operador: null,
    filtroStatusRack: 'TODOS',
    filtroCategoriaRack: 'TODAS',
    filtroCategoriaCatalogo: 'TODAS'
  };

  // 4.1 Carregamento e Autenticação
  async function carregarOperadorLogado() {
    try {
      const res = await API.auth.me();
      estadoApp.operador = res.data;
      document.getElementById('operator-name').textContent = estadoApp.operador.nome;
      document.getElementById('operator-role').textContent = estadoApp.operador.cargo;
      fecharModal('modal-login');
    } catch {
      abrirModal('modal-login');
    }
  }

  // 4.2 Renderização do Rack de Quartos (RF-004)
  async function atualizarRack() {
    const grid = document.getElementById('rooms-grid');
    if (!grid) return;

    grid.innerHTML = '<div style="padding: 24px; color: var(--text-muted); font-size: 0.9rem;">Carregando acomodações...</div>';

    try {
      const res = await API.acomodacoes.listar(estadoApp.filtroCategoriaRack);
      let quartos = res.data || [];

      // Atualiza contadores
      const total = quartos.length;
      const disp = quartos.filter(q => q.status === 'DISPONIVEL').length;
      const ocup = quartos.filter(q => q.status === 'OCUPADO').length;
      const limp = quartos.filter(q => q.status === 'LIMPEZA').length;
      const manut = quartos.filter(q => q.status === 'MANUTENCAO').length;
      const taxa = total > 0 ? Math.round((ocup / total) * 100) : 0;

      document.getElementById('stat-disponiveis').textContent = disp;
      document.getElementById('stat-ocupados').textContent = ocup;
      document.getElementById('stat-limpeza').textContent = limp;
      document.getElementById('stat-manutencao').textContent = manut;
      document.getElementById('stat-taxa').textContent = taxa + ' %';

      document.getElementById('count-todos').textContent = total;
      document.getElementById('count-disp').textContent = disp;
      document.getElementById('count-ocup').textContent = ocup;
      document.getElementById('count-limp').textContent = limp;
      document.getElementById('count-manut').textContent = manut;
      document.getElementById('badge-total-quartos').textContent = total;

      // Filtra por status visual
      if (estadoApp.filtroStatusRack !== 'TODOS') {
        quartos = quartos.filter(q => q.status === estadoApp.filtroStatusRack);
      }

      if (quartos.length === 0) {
        grid.innerHTML = '<div style="padding: 30px; text-align: center; color: var(--text-muted); grid-column: 1/-1;">Nenhum quarto encontrado com os filtros selecionados.</div>';
        return;
      }

      grid.innerHTML = '';
      quartos.forEach(q => {
        const card = document.createElement('div');
        card.className = `room-card ${q.status.toLowerCase()}`;

        let statusClass = 'status-badge ';
        let statusTexto = q.status;
        if (q.status === 'DISPONIVEL') {
          statusClass += 'status-badge-disponivel';
          statusTexto = 'DISPONÍVEL';
        } else if (q.status === 'OCUPADO') {
          statusClass += 'status-badge-ocupado';
          statusTexto = 'OCUPADO';
        } else if (q.status === 'LIMPEZA') {
          statusClass += 'status-badge-limpeza';
          statusTexto = 'EM LIMPEZA';
        } else if (q.status === 'MANUTENCAO') {
          statusClass += 'status-badge-manutencao';
          statusTexto = 'MANUTENÇÃO';
        }

        let conteudoOcupacao = '';
        if (q.status === 'OCUPADO') {
          conteudoOcupacao = `
            <div style="background: var(--bg-subtle); padding: 8px 10px; border-radius: 6px; margin: 8px 0; font-size: 0.8rem;">
              <div>Hóspede: <strong>${q.hospede_nome || 'Identificado'}</strong></div>
              <div>Entrada: <span style="color: var(--text-muted);">${formatarData(q.data_checkin)}</span></div>
            </div>
          `;
        }

        let botoesAcao = '';
        if (q.status === 'DISPONIVEL') {
          botoesAcao = `
            <button class="btn-primary btn-acao-checkin" data-quarto-uuid="${q.uuid_quarto}" data-quarto-num="${q.numero}" style="width: 100%; justify-content: center; font-size: 0.82rem; height: 32px;">
              Fazer Check-in
            </button>
          `;
        } else if (q.status === 'OCUPADO') {
          botoesAcao = `
            <div style="display: flex; gap: 6px;">
              <button class="btn-primary btn-acao-extrato" data-estadia-uuid="${q.uuid_hospedagem_ativa}" data-quarto-num="${q.numero}" style="flex: 1; justify-content: center; font-size: 0.78rem; height: 32px; background: #0284c7;">
                Extrato
              </button>
              <button class="btn-primary btn-acao-checkout" data-estadia-uuid="${q.uuid_hospedagem_ativa}" data-quarto-num="${q.numero}" data-hospede-nome="${q.hospede_nome}" data-tarifa="${q.preco_diaria}" data-entrada="${q.data_checkin}" style="flex: 1; justify-content: center; font-size: 0.78rem; height: 32px; background: #dc2626;">
                Checkout
              </button>
            </div>
          `;
        } else if (q.status === 'LIMPEZA') {
          botoesAcao = `
            <button class="btn-primary btn-acao-liberar-limpeza" data-quarto-uuid="${q.uuid_quarto}" style="width: 100%; justify-content: center; font-size: 0.82rem; height: 32px; background: #16a34a;">
              ✓ Concluir Limpeza
            </button>
          `;
        } else if (q.status === 'MANUTENCAO') {
          botoesAcao = `
            <button class="btn-secondary btn-acao-liberar-manutencao" data-quarto-uuid="${q.uuid_quarto}" style="width: 100%; justify-content: center; font-size: 0.82rem; height: 32px;">
              ✓ Liberar Quarto
            </button>
          `;
        }

        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div>
              <span class="room-number">${q.numero}</span>
              <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 6px;">${q.andar}º Andar</span>
            </div>
            <span class="${statusClass}">${statusTexto}</span>
          </div>
          <div style="font-size: 0.85rem; font-weight: 500; color: var(--text-main); margin-bottom: 4px;">
            ${q.categoria.replace('_', ' ')}
          </div>
          <div style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 8px;">
            ${q.caracteristicas || 'Completo com Ar e Wi-Fi'}
          </div>
          <div style="font-size: 0.88rem; font-weight: 600; color: var(--brand-navy); margin-bottom: 8px;">
            ${formatarMoeda(q.preco_diaria)} <span style="font-size: 0.72rem; font-weight: normal; color: var(--text-muted);">/ noite</span>
          </div>
          ${conteudoOcupacao}
          <div style="margin-top: 10px;">${botoesAcao}</div>
        `;

        grid.appendChild(card);
      });

      // Vincula eventos dos botões dos cards
      grid.querySelectorAll('.btn-acao-checkin').forEach(btn => {
        btn.addEventListener('click', () => abrirModalCheckin(btn.dataset.quartoUuid, btn.dataset.quartoNum));
      });
      grid.querySelectorAll('.btn-acao-checkout').forEach(btn => {
        btn.addEventListener('click', () => abrirModalCheckout(btn.dataset));
      });
      grid.querySelectorAll('.btn-acao-extrato').forEach(btn => {
        btn.addEventListener('click', () => abrirModalExtrato(btn.dataset.estadiaUuid, btn.dataset.quartoNum));
      });
      grid.querySelectorAll('.btn-acao-liberar-limpeza').forEach(btn => {
        btn.addEventListener('click', async () => {
          await API.acomodacoes.alterarStatus(btn.dataset.quartoUuid, 'DISPONIVEL');
          showToast('Quarto higienizado e disponível para hospedagem!', 'success');
          atualizarRack();
        });
      });
      grid.querySelectorAll('.btn-acao-liberar-manutencao').forEach(btn => {
        btn.addEventListener('click', async () => {
          await API.acomodacoes.alterarStatus(btn.dataset.quartoUuid, 'DISPONIVEL');
          showToast('Manutenção finalizada. Quarto liberado!', 'success');
          atualizarRack();
        });
      });
    } catch (err) {
      showToast('Erro ao atualizar Rack: ' + err.message, 'error');
    }
  }

  // 4.3 Renderização de Hóspedes (RF-001 & RF-002)
  async function atualizarHospedes(termo = '') {
    const tbody = document.getElementById('tbody-hospedes');
    if (!tbody) return;

    try {
      const res = await API.hospedes.listar(termo);
      const hospedes = res.data || [];
      document.getElementById('badge-total-hospedes').textContent = hospedes.length;

      if (hospedes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">Nenhum hóspede localizado.</td></tr>';
        return;
      }

      tbody.innerHTML = '';
      hospedes.forEach(h => {
        const tr = document.createElement('tr');
        const badgeAtivo = h.ativo
          ? '<span style="color: #166534; background: #dcfce7; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">Ativo</span>'
          : '<span style="color: #991b1b; background: #fee2e2; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">Inativo</span>';

        tr.innerHTML = `
          <td><strong>${h.nome}</strong></td>
          <td>${formatarCPF(h.cpf)}</td>
          <td>${h.email}</td>
          <td>${h.telefone || '-'}</td>
          <td>${h.cidade ? h.cidade + '/' + h.estado : '-'}</td>
          <td>${badgeAtivo}</td>
          <td>
            <button class="btn-secondary btn-toggle-hospede" data-uuid="${h.uuid_hospede}" data-ativo="${h.ativo}" style="font-size: 0.75rem; padding: 4px 8px;">
              ${h.ativo ? 'Inativar' : 'Reativar'}
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      tbody.querySelectorAll('.btn-toggle-hospede').forEach(btn => {
        btn.addEventListener('click', async () => {
          const novoStatus = btn.dataset.ativo !== 'true';
          await API.hospedes.alterarStatus(btn.dataset.uuid, novoStatus);
          showToast(novoStatus ? 'Hóspede ativado com sucesso.' : 'Hóspede inativado.', 'info');
          atualizarHospedes(document.getElementById('search-hospedes').value);
        });
      });
    } catch (err) {
      showToast('Erro ao listar hóspedes: ' + err.message, 'error');
    }
  }

  // 4.4 Renderização de Operadores (RF-003)
  async function atualizarOperadores() {
    const tbody = document.getElementById('tbody-operadores');
    if (!tbody) return;

    try {
      const res = await API.operadores.listar();
      const operadores = res.data || [];
      document.getElementById('badge-total-operadores').textContent = operadores.length;

      tbody.innerHTML = '';
      operadores.forEach(op => {
        const tr = document.createElement('tr');
        const badgeAtivo = op.ativo
          ? '<span style="color: #166534; background: #dcfce7; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">Online / Ativo</span>'
          : '<span style="color: #991b1b; background: #fee2e2; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">Inativo</span>';

        tr.innerHTML = `
          <td><strong>${op.nome}</strong></td>
          <td>${op.email}</td>
          <td><span style="font-size: 0.78rem; font-weight: 600; color: var(--brand-navy);">${op.cargo}</span></td>
          <td>${badgeAtivo}</td>
          <td>${formatarDataHora(op.criado_em)}</td>
          <td>
            <button class="btn-secondary btn-toggle-operador" data-uuid="${op.uuid_operador}" data-ativo="${op.ativo}" style="font-size: 0.75rem; padding: 4px 8px;">
              ${op.ativo ? 'Desativar' : 'Reativar'}
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      tbody.querySelectorAll('.btn-toggle-operador').forEach(btn => {
        btn.addEventListener('click', async () => {
          const novoStatus = btn.dataset.ativo !== 'true';
          await API.operadores.alterarStatus(btn.dataset.uuid, novoStatus);
          showToast(novoStatus ? 'Operador ativado.' : 'Operador desativado.', 'info');
          atualizarOperadores();
        });
      });
    } catch (err) {
      showToast('Erro ao carregar operadores: ' + err.message, 'error');
    }
  }

  // 4.5 Renderização de Catálogo e Consumo (RF-005)
  async function atualizarCatalogo() {
    const tbody = document.getElementById('tbody-catalogo');
    if (!tbody) return;

    try {
      const res = await API.consumo.listarCatalogo(estadoApp.filtroCategoriaCatalogo);
      const itens = res.data || [];

      tbody.innerHTML = '';
      itens.forEach(it => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><code>${it.codigo}</code></td>
          <td><strong>${it.nome}</strong></td>
          <td><span style="font-size: 0.75rem; color: var(--text-muted);">${it.categoria}</span></td>
          <td><strong>${formatarMoeda(it.preco_unitario)}</strong></td>
          <td style="color: var(--text-muted); font-size: 0.82rem;">${it.descricao || '-'}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (err) {
      showToast('Erro ao carregar catálogo: ' + err.message, 'error');
    }
  }

  // 4.6 Renderização de Governança e Manutenção (RF-006)
  async function atualizarGovernanca() {
    const tbody = document.getElementById('tbody-governanca');
    if (!tbody) return;

    try {
      const res = await API.governanca.listar();
      const ordens = res.data || [];

      const pendentes = ordens.filter(o => o.status === 'PENDENTE').length;
      const execucao = ordens.filter(o => o.status === 'EM_EXECUCAO').length;
      const concluidas = ordens.filter(o => o.status === 'CONCLUIDA').length;

      const statPend = document.getElementById('stat-gov-pendentes');
      if (statPend) statPend.textContent = pendentes;
      const statExec = document.getElementById('stat-gov-execucao');
      if (statExec) statExec.textContent = execucao;
      const statConc = document.getElementById('stat-gov-concluidas');
      if (statConc) statConc.textContent = concluidas;
      const statTot = document.getElementById('stat-gov-total');
      if (statTot) statTot.textContent = ordens.length;
      const badgeGov = document.getElementById('badge-total-governanca');
      if (badgeGov) badgeGov.textContent = pendentes + execucao;

      tbody.innerHTML = '';
      if (ordens.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">Nenhuma ordem de serviço registrada.</td></tr>';
        return;
      }

      ordens.forEach(o => {
        const tr = document.createElement('tr');

        let prioridadeClass = 'badge-media';
        if (o.prioridade === 'ALTA') prioridadeClass = 'badge-alta';
        if (o.prioridade === 'BAIXA') prioridadeClass = 'badge-baixa';

        let statusClass = 'badge-pendente';
        if (o.status === 'CONCLUIDA') statusClass = 'badge-concluida';
        if (o.status === 'EM_EXECUCAO') statusClass = 'badge-execucao';

        let acaoBotao = '';
        if (o.status !== 'CONCLUIDA') {
          acaoBotao = `
            <button class="btn-primary btn-concluir-os-main" data-uuid="${o.uuid_os}" data-codigo="${o.codigo_os}" data-quarto="${o.quarto_numero}" style="font-size: 0.75rem; padding: 4px 10px; background: #16a34a;">
              ✓ Concluir & Liberar
            </button>
          `;
        } else {
          acaoBotao = '<span style="color: #16a34a; font-size: 0.75rem; font-weight: 600;">✓ Concluída</span>';
        }

        tr.innerHTML = `
          <td><strong>${o.codigo_os}</strong></td>
          <td><strong>Quarto ${o.quarto_numero}</strong></td>
          <td><span style="font-size: 0.78rem;">${o.tipo}</span></td>
          <td><span class="${prioridadeClass}">${o.prioridade}</span></td>
          <td><span class="badge-status ${statusClass}">${o.status}</span></td>
          <td style="max-width: 260px; font-size: 0.8rem; color: var(--text-muted);">${o.descricao}</td>
          <td>${o.responsavel || '-'}</td>
          <td>${acaoBotao}</td>
        `;
        tbody.appendChild(tr);
      });

      tbody.querySelectorAll('.btn-concluir-os-main').forEach(btn => {
        btn.addEventListener('click', async () => {
          await API.governanca.concluir(btn.dataset.uuid);
          showToast(`Ordem ${btn.dataset.codigo} concluída! Quarto ${btn.dataset.quarto} liberado no Rack.`, 'success');
          atualizarGovernanca();
          atualizarRack();
        });
      });
    } catch (err) {
      showToast('Erro ao listar ordens de serviço: ' + err.message, 'error');
    }
  }

  // 4.6 Modais e Ações
  function abrirModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('active');
  }

  function fecharModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active');
  }

  async function abrirModalCheckin(uuidQuarto, numeroQuarto) {
    document.getElementById('checkin-quarto-uuid').value = uuidQuarto;
    document.getElementById('checkin-modal-quarto-num').textContent = numeroQuarto;

    // Popula select de hóspedes ativos
    const select = document.getElementById('checkin-select-hospede');
    select.innerHTML = '<option value="">Selecione um hóspede cadastrado...</option>';
    const res = await API.hospedes.listar();
    (res.data || []).filter(h => h.ativo).forEach(h => {
      const opt = document.createElement('option');
      opt.value = h.uuid_hospede;
      opt.textContent = `${h.nome} (CPF: ${formatarCPF(h.cpf)})`;
      select.appendChild(opt);
    });

    // Sugere saída em 2 dias
    const d = new Date();
    d.setDate(d.getDate() + 2);
    document.getElementById('checkin-data-saida').value = d.toISOString().slice(0, 16);

    abrirModal('modal-checkin');
  }

  function abrirModalCheckout(dados) {
    document.getElementById('checkout-hospedagem-uuid').value = dados.estadiaUuid;
    document.getElementById('checkout-quarto-num').textContent = dados.quartoNum;
    document.getElementById('checkout-hospede-nome').textContent = dados.hospedeNome;
    document.getElementById('checkout-data-entrada').textContent = formatarDataHora(dados.entrada);
    document.getElementById('checkout-tarifa-diaria').textContent = formatarMoeda(dados.tarifa) + ' / diária';
    abrirModal('modal-checkout');
  }

  async function abrirModalExtrato(uuidHospedagem, numQuarto) {
    document.getElementById('extrato-quarto-num').textContent = numQuarto;
    const res = await API.consumo.obterExtrato(uuidHospedagem);
    const extrato = res.data;

    document.getElementById('extrato-total-consumo').textContent = formatarMoeda(extrato.valor_total_consumo);

    const tbody = document.getElementById('tbody-extrato-itens');
    tbody.innerHTML = '';

    if (extrato.itens.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 16px;">Nenhum consumo lançado para esta estadia.</td></tr>';
    } else {
      extrato.itens.forEach(it => {
        const tr = document.createElement('tr');
        const estornado = it.status === 'ESTORNADO';
        tr.style.textDecoration = estornado ? 'line-through' : 'none';
        tr.style.color = estornado ? 'var(--text-muted)' : 'inherit';

        tr.innerHTML = `
          <td><strong>${it.nome_item}</strong></td>
          <td>${it.quantidade}</td>
          <td>${formatarMoeda(it.preco_unitario)}</td>
          <td><strong>${formatarMoeda(it.subtotal)}</strong></td>
          <td><span style="font-size: 0.75rem; color: ${estornado ? '#dc2626' : '#166534'}">${it.status}</span></td>
          <td>
            ${!estornado ? `<button class="btn-secondary btn-estornar-item" data-cons-uuid="${it.uuid_consumo}" style="font-size: 0.72rem; padding: 2px 6px;">Estornar</button>` : '<span style="font-size: 0.72rem;">-</span>'}
          </td>
        `;
        tbody.appendChild(tr);
      });

      tbody.querySelectorAll('.btn-estornar-item').forEach(btn => {
        btn.addEventListener('click', async () => {
          if (confirm('Confirma o estorno deste item no quarto?')) {
            await API.consumo.estornar(btn.dataset.consUuid);
            showToast('Item estornado com sucesso!', 'info');
            abrirModalExtrato(uuidHospedagem, numQuarto);
            atualizarRack();
          }
        });
      });
    }

    abrirModal('modal-extrato-consumo');
  }

  async function abrirModalLancarConsumo() {
    const selEstadia = document.getElementById('consumo-select-hospedagem');
    selEstadia.innerHTML = '<option value="">Selecione o quarto com hóspede...</option>';

    const resHosp = await API.hospedagens.listarAtivas();
    (resHosp.data || []).forEach(e => {
      const opt = document.createElement('option');
      opt.value = e.uuid_hospedagem;
      opt.textContent = `Quarto ${e.quarto_numero} — ${e.hospede_nome}`;
      selEstadia.appendChild(opt);
    });

    const selItem = document.getElementById('consumo-select-item');
    selItem.innerHTML = '<option value="">Selecione o item do catálogo...</option>';
    const resCat = await API.consumo.listarCatalogo();
    (resCat.data || []).forEach(it => {
      const opt = document.createElement('option');
      opt.value = it.uuid_item;
      opt.textContent = `${it.nome} — ${formatarMoeda(it.preco_unitario)}`;
      selItem.appendChild(opt);
    });

    abrirModal('modal-lancar-consumo');
  }

  // =========================================================================
  // 5. INICIALIZAÇÃO DE EVENT LISTENERS DO DOM
  // =========================================================================

  document.addEventListener('DOMContentLoaded', () => {
    // 5.1 Navegação por Abas
    const tabButtons = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        tabButtons.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));

        btn.classList.add('active');
        const targetId = btn.dataset.tab;
        const targetContent = document.getElementById(targetId);
        if (targetContent) targetContent.classList.add('active');

        // Gatilho de atualização sob demanda
        if (targetId === 'view-rack') atualizarRack();
        if (targetId === 'view-hospedes') atualizarHospedes();
        if (targetId === 'view-operadores') atualizarOperadores();
        if (targetId === 'view-consumo') atualizarCatalogo();
        if (targetId === 'view-governanca') atualizarGovernanca();
      });
    });

    // 5.2 Filtros do Rack
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        filterButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        estadoApp.filtroStatusRack = btn.dataset.filter;
        atualizarRack();
      });
    });

    const selectCategory = document.getElementById('filter-category');
    if (selectCategory) {
      selectCategory.addEventListener('change', () => {
        estadoApp.filtroCategoriaRack = selectCategory.value;
        atualizarRack();
      });
    }

    const btnAtualizarRack = document.getElementById('btn-atualizar-rack');
    if (btnAtualizarRack) {
      btnAtualizarRack.addEventListener('click', () => {
        atualizarRack();
        showToast('Rack sincronizado com LocalStorage.', 'info');
      });
    }

    // 5.3 Busca de Hóspedes
    const searchHospedes = document.getElementById('search-hospedes');
    if (searchHospedes) {
      searchHospedes.addEventListener('input', (e) => {
        atualizarHospedes(e.target.value);
      });
    }

    // 5.4 Formulário de Check-in
    const btnConfirmarCheckin = document.getElementById('btn-confirmar-checkin');
    if (btnConfirmarCheckin) {
      btnConfirmarCheckin.addEventListener('click', async () => {
        const uuidQuarto = document.getElementById('checkin-quarto-uuid').value;
        const uuidHospede = document.getElementById('checkin-select-hospede').value;
        const dataSaida = document.getElementById('checkin-data-saida').value;
        const acompanhantes = document.getElementById('checkin-acompanhantes').value;
        const obs = document.getElementById('checkin-observacoes').value;

        if (!uuidHospede) {
          alert('Por favor, selecione um hóspede titular.');
          return;
        }

        try {
          await API.hospedagens.checkin({
            uuid_quarto: uuidQuarto,
            uuid_hospede: uuidHospede,
            previsao_saida: dataSaida,
            acompanhantes: acompanhantes,
            observacoes: obs
          });
          fecharModal('modal-checkin');
          showToast('Check-in realizado com sucesso! Quarto Ocupado.', 'success');
          atualizarRack();
        } catch (err) {
          alert('Erro no check-in: ' + err.message);
        }
      });
    }

    // 5.5 Formulário de Check-out
    const btnConfirmarCheckout = document.getElementById('btn-confirmar-checkout');
    if (btnConfirmarCheckout) {
      btnConfirmarCheckout.addEventListener('click', async () => {
        const uuidHospedagem = document.getElementById('checkout-hospedagem-uuid').value;
        try {
          const res = await API.hospedagens.checkout(uuidHospedagem);
          fecharModal('modal-checkout');
          showToast(`Checkout concluído! Total: ${formatarMoeda(res.data.valor_total)}. Quarto enviado para Limpeza.`, 'success');
          atualizarRack();
        } catch (err) {
          alert('Erro no checkout: ' + err.message);
        }
      });
    }

    // 5.6 Cadastro de Novo Hóspede (RF-001)
    const btnAbrirCriarHospede = document.getElementById('btn-abrir-criar-hospede');
    if (btnAbrirCriarHospede) {
      btnAbrirCriarHospede.addEventListener('click', () => abrirModal('modal-criar-hospede'));
    }

    const formCriarHospede = document.getElementById('form-criar-hospede');
    if (formCriarHospede) {
      formCriarHospede.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          await API.hospedes.criar({
            nome: document.getElementById('hospede-criar-nome').value,
            cpf: document.getElementById('hospede-criar-cpf').value,
            email: document.getElementById('hospede-criar-email').value,
            telefone: document.getElementById('hospede-criar-telefone').value,
            data_nascimento: document.getElementById('hospede-criar-data-nasc').value
          });
          fecharModal('modal-criar-hospede');
          formCriarHospede.reset();
          showToast('Hóspede cadastrado com sucesso!', 'success');
          atualizarHospedes();
        } catch (err) {
          alert(err.message);
        }
      });
    }

    // 5.7 Cadastro de Novo Operador (RF-003)
    const btnAbrirCriarOperador = document.getElementById('btn-abrir-criar-operador');
    if (btnAbrirCriarOperador) {
      btnAbrirCriarOperador.addEventListener('click', () => abrirModal('modal-criar-operador'));
    }

    const formCriarOperador = document.getElementById('form-criar-operador');
    if (formCriarOperador) {
      formCriarOperador.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          await API.operadores.criar({
            nome: document.getElementById('operador-criar-nome').value,
            email: document.getElementById('operador-criar-email').value,
            cargo: document.getElementById('operador-criar-cargo').value
          });
          fecharModal('modal-criar-operador');
          formCriarOperador.reset();
          showToast('Novo operador cadastrado na equipe!', 'success');
          atualizarOperadores();
        } catch (err) {
          alert(err.message);
        }
      });
    }

    // 5.8 Lançamento de Consumo (RF-005)
    const btnAbrirLancarConsumo = document.getElementById('btn-abrir-lancar-consumo');
    if (btnAbrirLancarConsumo) {
      btnAbrirLancarConsumo.addEventListener('click', abrirModalLancarConsumo);
    }

    const formLancarConsumo = document.getElementById('form-lancar-consumo');
    if (formLancarConsumo) {
      formLancarConsumo.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          await API.consumo.lancar({
            uuid_hospedagem: document.getElementById('consumo-select-hospedagem').value,
            uuid_item: document.getElementById('consumo-select-item').value,
            quantidade: document.getElementById('consumo-quantidade').value
          });
          fecharModal('modal-lancar-consumo');
          formLancarConsumo.reset();
          showToast('Consumo lançado no quarto com sucesso!', 'success');
          atualizarRack();
        } catch (err) {
          alert(err.message);
        }
      });
    }

    // 5.9 Filtro do Catálogo
    const filterCat = document.getElementById('filter-catalogo-cat') || document.getElementById('filter-catalogo-category');
    if (filterCat) {
      filterCat.addEventListener('change', () => {
        estadoApp.filtroCategoriaCatalogo = filterCat.value;
        atualizarCatalogo();
      });
    }

    // 5.10 Governança e Manutenção (RF-006)
    const btnAbrirNovaOS = document.getElementById('btn-abrir-nova-os-main');
    if (btnAbrirNovaOS) {
      btnAbrirNovaOS.addEventListener('click', () => abrirModal('modal-nova-os-main'));
    }

    const formNovaOS = document.getElementById('form-nova-os-main');
    if (formNovaOS) {
      formNovaOS.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const quarto = document.getElementById('os-main-quarto').value;
          const tipo = document.getElementById('os-main-tipo').value;
          const prioridade = document.getElementById('os-main-prioridade').value;
          const responsavel = document.getElementById('os-main-responsavel').value;
          const descricao = document.getElementById('os-main-descricao').value;

          const res = await API.governanca.criar({
            quarto_numero: quarto,
            tipo: tipo,
            prioridade: prioridade,
            responsavel: responsavel,
            descricao: descricao
          });

          fecharModal('modal-nova-os-main');
          formNovaOS.reset();
          showToast(`Ordem de Serviço ${res.data.codigo_os} aberta com sucesso!`, 'success');
          atualizarGovernanca();
          atualizarRack();
        } catch (err) {
          alert('Erro ao abrir OS: ' + err.message);
        }
      });
    }

    // 5.11 Botão de Fechar Modais
    document.querySelectorAll('.modal-close, .btn-secondary').forEach(btn => {
      btn.addEventListener('click', () => {
        const modal = btn.closest('.modal-overlay');
        if (modal && modal.id !== 'modal-login') modal.classList.remove('active');
      });
    });

    // 5.11 Formulário de Login
    const formLogin = document.getElementById('form-login');
    if (formLogin) {
      formLogin.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const email = document.getElementById('login-email').value;
          const senha = document.getElementById('login-senha').value;
          const res = await API.auth.login(email, senha);
          showToast(`Bem-vindo(a), ${res.data.operador.nome}!`, 'success');
          fecharModal('modal-login');
          carregarOperadorLogado();
        } catch (err) {
          alert(err.message);
        }
      });
    }

    // 5.12 Botão de Logout
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) {
      btnLogout.addEventListener('click', async () => {
        if (confirm('Deseja encerrar a sessão atual?')) {
          await API.auth.logout();
          abrirModal('modal-login');
        }
      });
    }

    // 5.13 Botão de Reset do Banco de Demonstração
    const btnResetDB = document.getElementById('btn-reset-db');
    if (btnResetDB) {
      btnResetDB.addEventListener('click', () => {
        if (confirm('Deseja restaurar os dados originais da demonstração? Todos os quartos e testes voltarão ao estado padrão de apresentação.')) {
          LocalStorageDB.inicializar(true);
          showToast('Banco de dados LocalStorage restaurado para o estado de demonstração!', 'success');
          carregarOperadorLogado();
          atualizarRack();
          atualizarHospedes();
          atualizarOperadores();
          atualizarCatalogo();
          atualizarGovernanca();
        }
      });
    }

    // Inicialização da tela inicial
    carregarOperadorLogado();
    atualizarRack();
    atualizarHospedes();
    atualizarOperadores();
    atualizarCatalogo();
    atualizarGovernanca();
  });

})();
