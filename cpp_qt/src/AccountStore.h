#pragma once

#include <QDateTime>
#include <QString>

struct AccountState {
    bool loggedIn = false;
    QString email;
    QString displayName;
    QString plan = QStringLiteral("Guest");
    QString expiresAt;
    QString message;
};

class AccountStore {
public:
    AccountStore();

    AccountState currentState() const;
    AccountState registerUser(
        const QString& email,
        const QString& password,
        const QString& displayName
    );
    AccountState login(const QString& email, const QString& password);
    AccountState redeemCard(const QString& rawCode);
    void logout();

private:
    QString storePath() const;
    QString normalizedEmail(const QString& email) const;
    QString passwordHash(const QString& email, const QString& password) const;
    QString readText() const;
    void writeText(const QString& text) const;
};
