#include "MainWindow.h"

#include <QApplication>

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    QApplication::setApplicationName(QStringLiteral("C盘清理精灵"));
    QApplication::setOrganizationName(QStringLiteral("ClearC"));

    MainWindow window;
    window.show();
    return app.exec();
}
