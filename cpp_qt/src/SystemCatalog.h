#pragma once

#include <QString>
#include <QStringList>
#include <QVector>

struct OptimizerItem {
    QString id;
    QString tab;
    QString title;
    QString location;
    QString description;
    QString command;
    QString actionLabel = QStringLiteral("处理");
    QString iconHint;
    bool recommended = true;
    bool checkOnly = false;
    QStringList children;
};

struct BxItem {
    QString category;
    QString title;
    QString description;
    QString command;
    QString targetState;
    QString risk;
    bool basic = false;
    bool best = false;
};

struct RepairItem {
    QString id;
    QString title;
    QString risk;
    QString description;
    QString command;
    bool recommended = true;
};

class SystemCatalog {
public:
    static QVector<OptimizerItem> populateStartupItems();
    static QVector<OptimizerItem> populateMemoryItems();
    static QVector<OptimizerItem> populateSystemOptimizationItems();
    static QVector<OptimizerItem> populatePrivacyItems();
    static QVector<OptimizerItem> populateRegistryItems();
    static QVector<BxItem> bxItems();
    static QVector<RepairItem> repairActions();
    static QString runCommand(const QString& command, int* exitCode = nullptr);

private:
    static QVector<OptimizerItem> fallbackStartupItems();
    static QVector<OptimizerItem> fallbackMemoryItems();
};
