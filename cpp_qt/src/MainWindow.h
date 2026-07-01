#pragma once

#include "AccountStore.h"
#include "CleanupEngine.h"
#include "SystemCatalog.h"

#include <QCheckBox>
#include <QFutureWatcher>
#include <QLabel>
#include <QLineEdit>
#include <QMainWindow>
#include <QMap>
#include <QProgressBar>
#include <QPushButton>
#include <QStackedWidget>
#include <QTableWidget>
#include <QTabWidget>
#include <QTextEdit>
#include <QTreeWidget>

class MainWindow : public QMainWindow {
public:
    explicit MainWindow(QWidget* parent = nullptr);

private:
    QWidget* createSidebar();
    QWidget* createCleanPage();
    QWidget* createOptimizePage();
    QWidget* createBxPage();
    QWidget* createUninstallPage();
    QWidget* createFilePage();
    QWidget* createRepairPage();
    QWidget* createAccountPage();

    void applyStyle();
    void selectPage(int index);
    QPushButton* sidebarButton(const QString& text, int index);
    QPushButton* primaryButton(const QString& text) const;
    QPushButton* secondaryButton(const QString& text) const;
    void refreshDiskInfo();

    void startScan();
    void finishScan();
    void populateCleanupTree();
    void updateModeSelection(QCheckBox* changed);
    CleanupEngine::CleanMode currentCleanMode() const;
    QVector<CleanupEntry> selectedCleanupEntries() const;
    bool allowScanOnly() const;
    void cleanSelected();
    void cleanAllForCurrentMode();

    void populateStartupItems();
    void populateMemoryItems();
    void populateSystemOptimizationItems();
    void populatePrivacyItems();
    void populateRegistryItems();
    void populateOptimizerTable(QTreeWidget* table, const QVector<OptimizerItem>& items);
    void runOptimizerAction(const OptimizerItem& item);
    void applyCurrentOptimizationTab();

    void populateBxItems();
    void applyBxMode(const QString& mode);
    void applyBxOptimization();

    void refreshInstalledApps();
    void runUninstallCommand(const QString& command);

    void scanLargeFilesAsync();
    void scanDuplicateFilesAsync();
    void populateLargeFiles(const QVector<FileEntry>& files);
    void populateDuplicateFiles(const QVector<QVector<FileEntry>>& groups);
    void deleteSelectedFileItems();
    void scanFragments();
    void optimizeFragments();

    void populateRepairTable();
    void runRepairCommand(const RepairItem& item);
    void runSelectedRepairs();

    void refreshAccountState();
    void registerAccount();
    void loginAccount();
    void redeemCard();
    void logoutAccount();

    CleanupEngine cleanupEngine_;
    AccountStore accountStore_;
    QStackedWidget* pages_ = nullptr;
    QVector<QPushButton*> navButtons_;

    QLabel* totalSpaceLabel_ = nullptr;
    QLabel* usedSpaceLabel_ = nullptr;
    QLabel* freeSpaceLabel_ = nullptr;
    QLabel* reclaimSpaceLabel_ = nullptr;
    QLabel* currentScanPath = nullptr;
    QProgressBar* scanProgress_ = nullptr;
    QTreeWidget* cleanupTree_ = nullptr;
    QCheckBox* recommendedMode = nullptr;
    QCheckBox* professionalMode = nullptr;
    QCheckBox* selectAllMode = nullptr;
    QCheckBox* simulateMode_ = nullptr;
    QCheckBox* backupMode_ = nullptr;
    QVector<CleanupEntry> cleanupEntries_;
    QFutureWatcher<CleanupScanResult>* scanWatcher_ = nullptr;

    QTabWidget* optimizerTabs_ = nullptr;
    QMap<QString, QTreeWidget*> optimizerTables_;

    QTableWidget* uninstallTable_ = nullptr;
    QTabWidget* fileTabs_ = nullptr;
    QTableWidget* largeFileTable_ = nullptr;
    QTableWidget* duplicateFileTable_ = nullptr;
    QLabel* fileStatusLabel_ = nullptr;
    QTextEdit* repairLog_ = nullptr;
    QTableWidget* repairTable_ = nullptr;

    QLabel* accountStateLabel_ = nullptr;
    QLineEdit* accountEmailEdit_ = nullptr;
    QLineEdit* accountNameEdit_ = nullptr;
    QLineEdit* accountPasswordEdit_ = nullptr;
    QLineEdit* cardCodeEdit_ = nullptr;
};
