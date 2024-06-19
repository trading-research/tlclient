# auto generated by update_py.py
from ..database.connector import DatabaseConnector
from ..database.models import Account


class AccountHelper(object):

    def __init__(self):
        self.conn = DatabaseConnector(db='db_core')

    def save_account(self, acc_tag, acc_config, key_name, force=False):
        with self.conn.get_session() as session:
            # check existence
            account: Account = session.query(Account).filter(Account.acc_tag == acc_tag).one_or_none()
            if account is not None and not force:
                raise AssertionError('account "{}" already existed'.format(acc_tag))
            elif account is None:
                account = Account()
                session.add(account)
                account.set_create_time()
            account.set_update_time()
            account.acc_tag = acc_tag
            account.acc_config = acc_config
            account.key_name = key_name
            session.commit()
            print('done adding account "{}"'.format(acc_tag))

    def get_accounts(self, acc_tag=None):
        print('[AccountHelper] getting accounts from', self.conn)
        with self.conn.get_session() as session:
            query = session.query(Account)
            if acc_tag:
                query = query.filter(Account.acc_tag == acc_tag)
            accounts = query.all()

        return accounts

    def get_account(self, acc_tag) -> Account:
        accounts = self.get_accounts(acc_tag=acc_tag)
        assert len(accounts) <= 1, 'more than one account named "{}"'.format(acc_tag)
        if len(accounts):
            return accounts[0]
        else:
            return None

    def delete_account(self, acc_tag):
        print('to delete account "{}"'.format(acc_tag))
        with self.conn.get_session() as session:
            account = session.query(Account).filter(Account.acc_tag == acc_tag).one_or_none()
            if account is None:
                print('[warning] "{}" not existed'.format(acc_tag))
            else:
                session.delete(account)
                session.commit()
                print('done!')
