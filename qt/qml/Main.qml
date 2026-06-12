import QtCore
import QtQuick
import QtQuick.Controls.Material
import "components"

ApplicationWindow {
    id: window
    width: 1400
    height: 700
    minimumWidth: 1000
    minimumHeight: 500
    visible: true
    title: "Mila"
    color: Theme.background

    property bool force_close: false

    Material.theme: Material.Dark
    Material.accent: Theme.accent

    Settings {
        id: windowSettings
        category: "main"
        property alias window_width: window.width
        property alias window_height: window.height
        property alias window_x: window.x
        property alias window_y: window.y
    }

    onClosing: function (close) {
        if (downloader.running && !window.force_close) {
            close.accepted = false
            quitDialog.open()
        }
    }

    MilaDialog {
        id: quitDialog
        anchors.centerIn: Overlay.overlay
        modal: true
        title: "Quit"

        Label { text: "A download is running — cancel it and quit?" }

        footer: MilaDialogButtonBox {
            MilaButton {
                text: "Quit"
                variant: "ghost"
                destructive: true
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            }
            MilaButton {
                text: "Keep downloading"
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            }
        }

        onAccepted: {
            window.force_close = true
            downloader.shutdown()
            window.close()
        }
    }

    AppRoot { anchors.fill: parent }
}
