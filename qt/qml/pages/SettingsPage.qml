pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../components"

Page {
    id: page
    background: Rectangle { color: Theme.background }

    Connections {
        target: backend
        function onInvalid_setting(field, message) { toast.show_error(message) }
        function onNotice(message) { toast.show(message) }
        function onLogged_out(ok, message) {
            if (ok)
                toast.show(message)
            else
                toast.show_error(message)
        }
    }

    component FormRow : RowLayout {
        Layout.fillWidth: true
        spacing: 14
    }
    component FieldName : Label {
        color: Theme.text_secondary
        font.pixelSize: Theme.font_body
        Layout.preferredWidth: 160
    }
    component Field : Rectangle {
        property alias text: input.text
        property string placeholder: ""
        signal edited(string value)

        Layout.preferredWidth: 260
        implicitHeight: 38
        radius: Theme.radius_small
        color: Theme.field
        border.width: 1
        border.color: input.activeFocus ? Theme.accent : Theme.border

        TextInput {
            id: input
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            verticalAlignment: TextInput.AlignVCenter
            color: Theme.text_primary
            font.pixelSize: Theme.font_body
            clip: true
            selectByMouse: true
            onEditingFinished: parent.edited(text)
        }
        Label {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: parent.placeholder
            color: Theme.text_placeholder
            font.pixelSize: Theme.font_body
            visible: input.text.length === 0 && !input.activeFocus
        }
    }

    Flickable {
        id: flick
        anchors.fill: parent
        contentWidth: width
        contentHeight: content.height + 80
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: MilaScrollBar {}

        WheelHandler {
            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
            onWheel: function(event) {
                const max = Math.max(0, flick.contentHeight - flick.height)
                const dy = event.pixelDelta.y !== 0
                    ? event.pixelDelta.y
                    : event.angleDelta.y / 120 * 180
                flick.contentY = Math.max(0, Math.min(max, flick.contentY - dy))
                event.accepted = true
            }
        }

        ColumnLayout {
            id: content
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 40
            width: Math.min(flick.width - 96, 600)
            spacing: 18

            Label {
                text: "Settings"
                color: Theme.text_primary
                font.pixelSize: Theme.font_title
                font.weight: Font.ExtraBold
            }

            Rectangle {
                Layout.fillWidth: true
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.hairline
                implicitHeight: form.implicitHeight + 24

                ColumnLayout {
                    id: form
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 18

                    FormRow {
                        FieldName { text: "Username" }
                        Item { Layout.fillWidth: true }
                        Field {
                            text: backend.username
                            onEdited: function(value) { backend.username = value }
                        }
                    }
                    FormRow {
                        FieldName { text: "Steam account" }
                        Item { Layout.fillWidth: true }
                        Field {
                            placeholder: "required to download"
                            text: backend.steam_account
                            onEdited: function(value) { backend.steam_account = value }
                        }
                    }
                    FormRow {
                        FieldName { text: "Steam login" }
                        Item { Layout.fillWidth: true }
                        MilaButton {
                            variant: "ghost"
                            destructive: true
                            text: "Log out"
                            onClicked: logoutDialog.open()
                        }
                    }
                    FormRow {
                        FieldName { text: "RadminVPN IP" }
                        Item { Layout.fillWidth: true }
                        Field {
                            text: backend.radmin_ip
                            onEdited: function(value) { backend.radmin_ip = value }
                        }
                    }
                    FormRow {
                        FieldName { text: "Download speed" }
                        Item { Layout.fillWidth: true }
                        MilaOptionControl {
                            options: backend.speed_presets
                            current_value: backend.max_downloads
                            onPicked: function(value) { backend.max_downloads = value }
                        }
                    }
                    FormRow {
                        FieldName { text: "Discord Rich Presence" }
                        Item { Layout.fillWidth: true }
                        MilaOptionControl {
                            options: [{ label: "Off", value: false }, { label: "On", value: true }]
                            current_value: backend.discord_rpc
                            onPicked: function(value) { backend.discord_rpc = value }
                        }
                    }
                }
            }

            Label {
                text: "RadminVPN"
                color: Theme.text_primary
                font.pixelSize: Theme.font_title
                font.weight: Font.ExtraBold
                Layout.topMargin: 12
            }

            RadminSection {
                Layout.fillWidth: true
                toast: toast
            }
        }
    }

    MilaDialog {
        id: logoutDialog
        anchors.centerIn: Overlay.overlay
        modal: true
        width: 440
        title: "Log out"

        Label {
            width: logoutDialog.availableWidth
            text: "This wipes the cached DepotDownloader access token. Your next download will require password and Steam Guard entry."
            color: Theme.text_soft
            font.pixelSize: Theme.font_body
            wrapMode: Text.Wrap
        }

        footer: MilaDialogButtonBox {
            MilaButton {
                text: "Log out"
                variant: "primary"
                destructive: true
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            }
            MilaButton {
                text: "Cancel"
                variant: "ghost"
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            }
        }

        onAccepted: backend.log_out()
    }

    Toast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
    }
}
