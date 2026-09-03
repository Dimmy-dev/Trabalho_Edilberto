-- =====================================================================
-- Seeds de Demonstração: Sistema Grand Plaza Hotel Management
-- Requisito Funcional: RF-001 - Cadastro de Hóspede
-- =====================================================================

USE db_hotel_grand_plaza;

-- Inserção de Hóspedes Iniciais para Teste
INSERT INTO tb_hospedes (uuid_publico, nome, email, cpf, telefone, data_nascimento, observacoes)
VALUES 
    ('c4a1e944-938b-4c28-97f4-8d4cb28d2001', 'Carlos Eduardo Mendes', 'carlos.mendes@email.com', '12345678901', '11987654321', '1985-04-12', 'Cliente frequente. Prefere quartos em andares altos.'),
    ('d5b2f055-049c-5d39-08a5-9e5dc39e3002', 'Mariana Alencar Santos', 'mariana.alencar@email.com', '98765432100', '21998877665', '1992-09-28', 'Hóspede corporativa VIP. Necessita de mesa de trabalho.'),
    ('e6c3a166-150d-6e40-19b6-0f6ed4af4003', 'Roberto Guimarães Lima', 'roberto.guimaraes@email.com', '45678912300', '31977665544', '1978-11-05', 'Alergia a travesseiros de penas.')
ON DUPLICATE KEY UPDATE nome = VALUES(nome);

-- Inserção de Quartos Disponíveis
INSERT INTO tb_quartos (numero, categoria, valor_diaria, status)
VALUES
    ('101', 'Standard Single', 220.00, 'DISPONIVEL'),
    ('102', 'Standard Double', 310.00, 'DISPONIVEL'),
    ('201', 'Suíte Executiva', 520.00, 'DISPONIVEL'),
    ('301', 'Suíte Presidencial Grand Plaza', 1250.00, 'DISPONIVEL')
ON DUPLICATE KEY UPDATE valor_diaria = VALUES(valor_diaria);
