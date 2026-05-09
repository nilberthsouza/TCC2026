clc; clear; close all;

%% =========================
% Variáveis:
% x1=L6, x2=L7, ..., x26=L31
% ==========================

n = 26;

% Objetivo:
% minimizar soma dos comprimentos variáveis
f = ones(n,1);

%% =========================
% Igualdades (distâncias alvo)
% ==========================

Aeq = [];
beq = [];

% 812 -> 850 = 0.62
row = zeros(1,n);
row([1 2]) = 1;      % L6 L7
Aeq = [Aeq; row];
beq = [beq; 0.62];

% 812 -> 854 = 2.18
row = zeros(1,n);
row([1 2 19 4 8 9 10]) = 1;   % L6,L7,L24,L9,L13,L14,L15
Aeq = [Aeq; row];
beq = [beq; 2.18];

% 812 -> 822 = 3
row = zeros(1,n);
row([1 2 19 3 5 6]) = 1;      % L6,L7,L24,L8,L10,L11
Aeq = [Aeq; row];
beq = [beq; 3.0];

% 812 -> 834 = 4.05
row = zeros(1,n);
row([1 2 19 4 8 9 10 22 20 11 24]) = 1;
% L6,L7,L24,L9,L13,L14,L15,L27,L25,L16,L29
Aeq = [Aeq; row];
beq = [beq; 4.05];

% 812 -> 840 = 6.75
row = zeros(1,n);
row([1 2 19 4 8 9 10 22 20 11 24 12 25 14]) = 1;
% caminho até 834 + L17,L30,L19
Aeq = [Aeq; row];
beq = [beq; 6.75];

% 812 -> 848 = 7.47
row = zeros(1,n);
row([1 2 19 4 8 9 10 22 20 11 24 13 16 17 18]) = 1;
% caminho até 834 + L18,L21,L22,L23
Aeq = [Aeq; row];
beq = [beq; 7.47];

%% =========================
% Restrição de comprimento total
% ==========================

% Comprimento fixo até barra 812
Lfix = 0.488636 + 0.327652 + 0.5 + 0.9;

% Soma total <= 9.53
A = ones(1,n);
b = 9.53 - Lfix;

%% =========================
% Limites
% ==========================

eps_val = 1e-4;   % diferente de zero
lb = eps_val * ones(n,1);
ub = [];

%% =========================
% Resolver
% ==========================

options = optimoptions('linprog','Display','iter');

[x,fval,exitflag,output] = linprog(f,A,b,Aeq,beq,lb,ub,options);

%% =========================
% Resultados
% ==========================

names = { ...
    'L6','L7','L8','L9','L10','L11','L12','L13','L14','L15',...
    'L16','L17','L18','L19','L20','L21','L22','L23','L24','L25',...
    'L26','L27','L28','L29','L30','L31'};

disp('===== SOLUCAO =====');
for i=1:n
    fprintf('%s = %.6f mi\n', names{i}, x(i));
end

fprintf('\nSoma variaveis = %.6f mi\n', sum(x));
fprintf('Total alimentador = %.6f mi\n', sum(x)+Lfix);