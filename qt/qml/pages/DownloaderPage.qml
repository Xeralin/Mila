pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../components"

Page {
    id: page

    background: Rectangle { color: Theme.background }

    function season_name(key) {
        const seasons = backend.all_seasons
        for (let i = 0; i < seasons.length; i++) {
            if (seasons[i].key === key)
                return seasons[i].code + " " + seasons[i].name
        }
        return key
    }

    StackView {
        id: stack
        anchors.fill: parent
        initialItem: listComponent
    }

    Component {
        id: listComponent

        ListView {
            id: list
            model: backend.all_seasons
            spacing: 0
            clip: true
            reuseItems: true
            boundsBehavior: Flickable.StopAtBounds

            property int wheel_step: 180

            WheelHandler {
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                onWheel: function(event) {
                    const max = Math.max(0, list.contentHeight - list.height)
                    const dy = event.pixelDelta.y !== 0
                        ? event.pixelDelta.y
                        : event.angleDelta.y / 120 * list.wheel_step
                    list.contentY = Math.max(0, Math.min(max, list.contentY - dy))
                    event.accepted = true
                }
            }

            delegate: Banner {
                id: banner
                required property var modelData

                width: list.width
                code: banner.modelData.code
                title: banner.modelData.name
                hasSplash: banner.modelData.has_splash
                splashSource: banner.modelData.splash
                active: banner.modelData.key === downloader.active_key && downloader.running
                onActivated: stack.push(detailComponent, { season: banner.modelData })
            }

            ScrollBar.vertical: MilaScrollBar {}
        }
    }

    Component {
        id: detailComponent
        SeasonDetail { onBack: stack.pop() }
    }

    MilaDialog {
        id: loginDialog
        property string kind: "password"
        anchors.centerIn: Overlay.overlay
        modal: true
        closePolicy: Popup.NoAutoClose
        title: kind === "guard" ? "Steam Guard" : "Steam login"

        ColumnLayout {
            spacing: 12
            Label {
                text: loginDialog.kind === "guard"
                    ? "Enter your Steam Guard code"
                    : "Enter your Steam password"
            }
            MilaTextField {
                id: loginField
                Layout.preferredWidth: 260
                echoMode: loginDialog.kind === "guard" ? TextInput.Normal : TextInput.Password
                onAccepted: {
                    if (text.length > 0)
                        loginDialog.accept()
                }
            }
        }

        footer: MilaDialogButtonBox {
            MilaButton {
                text: "OK"
                variant: "primary"
                enabled: loginField.text.length > 0
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            }
            MilaButton {
                text: "Cancel"
                variant: "ghost"
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            }
        }

        onAccepted: {
            downloader.submit_login(loginField.text)
            loginField.clear()
        }
        onRejected: {
            loginField.clear()
            downloader.cancel()
        }
    }

    Toast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
    }

    Connections {
        target: downloader
        function onLogin_required(kind) {
            loginDialog.kind = kind
            loginField.clear()
            loginDialog.open()
            loginField.forceActiveFocus()
        }
        function onError(message) { toast.show_error(message) }
        function onFinished(code) {
            if (loginDialog.opened)
                loginDialog.close()
            if (code === 0)
                toast.show(page.season_name(downloader.active_key) + " installed")
            else if (downloader.state === "failed")
                toast.show_error("Download failed — exit code " + code)
        }
    }
}
