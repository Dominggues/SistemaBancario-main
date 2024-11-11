import textwrap
from abc import ABC, abstractclassmethod, abstractproperty
from datetime import datetime
from pathlib import Path

import customtkinter

ROOT_PATH = Path(__file__).parent


class ContasIterador:
    def __init__(self, contas):
        self.contas = contas
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        try:
            conta = self.contas[self._index]
            return f"""\
            Agência:\t{conta.agencia}
            Número:\t\t{conta.numero}
            Titular:\t{conta.cliente.nome}
            Saldo:\t\tR$ {conta.saldo:.2f}
        """
        except IndexError:
            raise StopIteration
        finally:
            self._index += 1


class Cliente:
    def __init__(self, endereco):
        self.endereco = endereco
        self.contas = []
        self.indice_conta = 0

    def realizar_transacao(self, conta, transacao):
        if len(conta.historico.transacoes_do_dia()) >= 10:
            print("\n@@@ Você excedeu o número de transações permitidas para hoje! @@@")
            return

        transacao.registrar(conta)

    def adicionar_conta(self, conta):
        self.contas.append(conta)


class PessoaFisica(Cliente):
    def __init__(self, nome, data_nascimento, cpf, endereco):
        super().__init__(endereco)
        self.nome = nome
        self.data_nascimento = data_nascimento
        self.cpf = cpf

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: ('{self.cpf}')>"


class Conta:
    def __init__(self, numero, cliente):
        self._saldo = 0
        self._numero = numero
        self._agencia = "0001"
        self._cliente = cliente
        self._historico = Historico()

    @classmethod
    def nova_conta(cls, cliente, numero):
        return cls(numero, cliente)

    @property
    def saldo(self):
        return self._saldo

    @property
    def numero(self):
        return self._numero

    @property
    def agencia(self):
        return self._agencia

    @property
    def cliente(self):
        return self._cliente

    @property
    def historico(self):
        return self._historico

    def sacar(self, valor):
        saldo = self.saldo
        excedeu_saldo = valor > saldo

        if excedeu_saldo:
            print("\n@@@ Operação falhou! Você não tem saldo suficiente. @@@")

        elif valor > 0:
            self._saldo -= valor
            print("\n Saque realizado com sucesso!")
            return True

        else:
            print("\n@@@ Operação falhou! O valor informado é inválido. @@@")

        return False

    def depositar(self, valor):
        if valor > 0:
            self._saldo += valor
            print("\nDepósito realizado com sucesso!")
        else:
            print("\n@@@ Operação falhou! O valor informado é inválido. @@@")
            return False

        return True


class ContaCorrente(Conta):
    def __init__(self, numero, cliente, limite=5000, limite_saques=3):
        super().__init__(numero, cliente)
        self._limite = limite
        self._limite_saques = limite_saques

    @classmethod
    def nova_conta(cls, cliente, numero, limite, limite_saques):
        return cls(numero, cliente, limite, limite_saques)

    def sacar(self, valor):
        numero_saques = len(
            [
                transacao
                for transacao in self.historico.transacoes
                if transacao["tipo"] == Saque.__name__
            ]
        )

        excedeu_limite = valor > self._limite
        excedeu_saques = numero_saques >= self._limite_saques

        if excedeu_limite:
            print("\n@@@ Operação falhou! O valor do saque excede o limite. @@@")

        elif excedeu_saques:
            print("\n@@@ Operação falhou! Número máximo de saques excedido. @@@")

        else:
            return super().sacar(valor)

        return False

    def __repr__(self):
        return f"<{self.__class__.__name__}: ('{self.agencia}', '{self.numero}', '{self.cliente.nome}')>"

    def __str__(self):
        return f"""\
            Agência:\t{self.agencia}
            C/C:\t\t{self.numero}
            Titular:\t{self.cliente.nome}
        """


class Historico:
    def __init__(self):
        self._transacoes = []

    @property
    def transacoes(self):
        return self._transacoes

    def adicionar_transacao(self, transacao):
        self._transacoes.append(
            {
                "tipo": transacao.__class__.__name__,
                "valor": transacao.valor,
                "data": datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S"),
            }
        )

    def gerar_relatorio(self, tipo_transacao=None):
        for transacao in self._transacoes:
            if (
                tipo_transacao is None
                or transacao["tipo"].lower() == tipo_transacao.lower()
            ):
                yield transacao

    def transacoes_do_dia(self):
        data_atual = datetime.utcnow().date()
        transacoes = []
        for transacao in self._transacoes:
            data_transacao = datetime.strptime(
                transacao["data"], "%d-%m-%Y %H:%M:%S"
            ).date()
            if data_atual == data_transacao:
                transacoes.append(transacao)
        return transacoes


class Transacao(ABC):
    @property
    @abstractproperty
    def valor(self):
        pass

    @abstractclassmethod
    def registrar(self, conta):
        pass


class Saque(Transacao):
    def __init__(self, valor):
        self._valor = valor

    @property
    def valor(self):
        return self._valor

    def registrar(self, conta):
        sucesso_transacao = conta.sacar(self.valor)

        if sucesso_transacao:
            conta.historico.adicionar_transacao(self)


class Deposito(Transacao):
    def __init__(self, valor):
        self._valor = valor

    @property
    def valor(self):
        return self._valor

    def registrar(self, conta):
        sucesso_transacao = conta.depositar(self.valor)

        if sucesso_transacao:
            conta.historico.adicionar_transacao(self)


def log_transacao(func):
    def envelope(*args, **kwargs):
        resultado = func(*args, **kwargs)
        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # TODO: alterar a implementação para salvar em arquivo.
        # f"[{data_hora}] Função '{func.__name__}' executada com argumentos {args} e {kwargs}. Retornou {result}\n"
        try:
            with open(ROOT_PATH / "log.txt", "a", encoding="utf-8") as arquivo_log:
                arquivo_log.write(f"[{data_hora}] Função: {func.__name__.upper()} ")
                arquivo_log.write(f"Executada com argumentos: {args} {kwargs}. ")
                arquivo_log.write(f"E retornou: {resultado}\n")
        except IOError as exc:
            print(f"Erro ao abrir arquivo {exc}")
        return resultado

    return envelope


def pegar_cpf(janela, title):
    cpf = customtkinter.CTkInputDialog(
        text="Informe o CPF do cliente:", title=title
    ).get_input()
    return cpf


def filtrar_cliente(cpf, clientes):
    clientes_filtrados = [cliente for cliente in clientes if cliente.cpf == cpf]
    return clientes_filtrados[0] if clientes_filtrados else None


def recuperar_conta_cliente(cliente):
    if not cliente.contas:
        print("\n@@@ Cliente não possui conta! @@@")
        return

    # FIXME: não permite cliente escolher a conta
    return cliente.contas[0]


@log_transacao
def depositar(clientes, janela):
    cpf = pegar_cpf(janela, "Depositar")
    cliente = filtrar_cliente(cpf, clientes)

    if not cliente:
        mensagem = customtkinter.CTkLabel(
            janela, text="\n@@@ Cliente não encontrado! @@@", text_color="red"
        )
        mensagem.pack(pady=10)
        janela.after(3000, mensagem.destroy)
        return

    valor = float(
        customtkinter.CTkInputDialog(
            text="Informe o valor do Depósito", title="Valor do Depósito"
        ).get_input()
    )
    transacao = Deposito(valor)

    conta = recuperar_conta_cliente(cliente)
    if not conta:
        return

    cliente.realizar_transacao(conta, transacao)

    mensagem = customtkinter.CTkLabel(
        janela, text="\nDepósito realizado com sucesso!", text_color="green"
    )
    mensagem.pack(pady=10)
    janela.after(3000, mensagem.destroy)


@log_transacao
def sacar(clientes, janela):
    cpf = pegar_cpf(janela, "Sacar")
    cliente = filtrar_cliente(cpf, clientes)

    if not cliente:
        mensagem = customtkinter.CTkLabel(
            janela, text="\n@@@ Cliente não encontrado! @@@", text_color="red"
        )
        mensagem.pack(pady=10)
        janela.after(3000, mensagem.destroy)
        return

    valor = float(
        customtkinter.CTkInputDialog(
            text="Informe o valor do Saque", title="Valor do Saque"
        ).get_input()
    )

    transacao = Saque(valor)

    conta = recuperar_conta_cliente(cliente)
    if not conta:
        return

    cliente.realizar_transacao(conta, transacao)

    mensagem = customtkinter.CTkLabel(
        janela, text="\n Saque realizado com sucesso!", text_color="green"
    )
    mensagem.pack(pady=10)
    janela.after(3000, mensagem.destroy)


@log_transacao
def exibir_extrato(clientes, janela):
    cpf = pegar_cpf(janela, "Criar cliente")
    cliente = filtrar_cliente(cpf, clientes)

    if not cliente:
        mensagem = customtkinter.CTkLabel(
            janela, text="\n@@@ Cliente não encontrado! @@@", text_color="red"
        )
        mensagem.pack(pady=10)
        janela.after(3000, mensagem.destroy)
        return

    conta = recuperar_conta_cliente(cliente)
    if not conta:
        return

    extrato = "\n================ EXTRATO ================"

    tem_transacao = False
    for transacao in conta.historico.gerar_relatorio():
        tem_transacao = True
        extrato += f"\n{transacao['data']}\n{transacao['tipo']}:\n\tR$ {transacao['valor']:.2f}"
        cor = "green"
    if not tem_transacao:
        extrato += "\nNão foram realizadas movimentações"
        cor = "red"
    extrato += f"\n\nSaldo:\n\tR$ {conta.saldo:.2f}\n=========================================="

    mensagem = customtkinter.CTkLabel(janela, text=extrato, text_color=cor)
    mensagem.pack(pady=10)


@log_transacao
def criar_cliente(clientes, janela):

    cpf = pegar_cpf(janela, "Criar cliente")
    cliente = filtrar_cliente(cpf, clientes)

    if cliente:
        mensagem = customtkinter.CTkLabel(
            janela, text="\n@@@ Já existe cliente com esse CPF! @@@", text_color="red"
        )
        mensagem.pack(pady=10)
        janela.after(5000, mensagem.destroy)
        return

    nome = customtkinter.CTkInputDialog(
        text="Informe o nome completo:", title="Nova Conta"
    ).get_input()
    data_nascimento = customtkinter.CTkInputDialog(
        text="Informe a data de nascimento (dd-mm-aaaa):", title="Nova Conta"
    ).get_input()
    endereco = customtkinter.CTkInputDialog(
        text="Informe o endereço (logradouro, nro - bairro - cidade/sigla estado):",
        title="Nova Conta",
    ).get_input()

    cliente = PessoaFisica(
        nome=nome, data_nascimento=data_nascimento, cpf=cpf, endereco=endereco
    )

    clientes.append(cliente)

    mensagem = customtkinter.CTkLabel(
        janela, text="\n Cliente criado com sucesso!", text_color="green"
    )
    mensagem.pack(pady=10)
    janela.after(3000, mensagem.destroy)


@log_transacao
def criar_conta(numero_conta, clientes, contas, janela):
    cpf = pegar_cpf(janela, "Criar conta")
    cliente = filtrar_cliente(cpf, clientes)

    if not cliente:
        mensagem = customtkinter.CTkLabel(
            janela,
            text="\n@@@ Cliente não encontrado, fluxo de criação de conta encerrado! @@@",
            text_color="red",
        )
        mensagem.pack(pady=10)
        janela.after(3000, mensagem.destroy)
        return

    conta = ContaCorrente.nova_conta(
        cliente=cliente, numero=numero_conta, limite=500, limite_saques=50
    )
    contas.append(conta)
    cliente.contas.append(conta)

    mensagem = customtkinter.CTkLabel(
        janela, text="\nConta criada com sucesso!", text_color="green"
    )
    mensagem.pack(pady=10)
    janela.after(3000, mensagem.destroy)


def listar_contas(contas, janela):
    for conta in ContasIterador(contas):
        conta_info = str(conta).strip()
        conta_info = textwrap.dedent(conta_info)
        mensagem = customtkinter.CTkLabel(
            janela, text=f"\n{conta_info}", text_color="green"
        )
        mensagem.pack(pady=10)


def main():
    clientes = []
    contas = []

    def selecionar_operacao(opcao):
        if opcao == "Novo Usuário":
            criar_cliente(clientes, janela)
        elif opcao == "Nova Conta":
            numero_conta = len(contas) + 1
            criar_conta(numero_conta, clientes, contas, janela)
        elif opcao == "Depositar":
            depositar(clientes, janela)
        elif opcao == "Sacar":
            sacar(clientes, janela)
        elif opcao == "Extrato":
            exibir_extrato(clientes, janela)
        elif opcao == "Listar contas":
            listar_contas(contas, janela)

    customtkinter.set_appearance_mode("dark")
    customtkinter.set_default_color_theme("dark-blue")

    janela = customtkinter.CTk()
    janela.title("Sistema Bancário - Davi Ryan Konuma Lima")
    janela.geometry("500x750")

    titulo = customtkinter.CTkLabel(janela, text="Seja bem vindo ao Sistema bancário!")
    texto_selecionar = customtkinter.CTkLabel(janela, text="Selecione a opção desejada")
    operacao_selecionada = customtkinter.CTkOptionMenu(
        janela,
        values=[
            "Novo Usuário",
            "Nova Conta",
            "Depositar",
            "Sacar",
            "Extrato",
            "Listar contas",
        ],
        command=selecionar_operacao,
    )
    titulo.pack(padx=10, pady=10)
    texto_selecionar.pack(padx=10, pady=10)
    operacao_selecionada.pack(padx=10, pady=10)
    janela.mainloop()


main()
