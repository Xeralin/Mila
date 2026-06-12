pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: section

    property var toast: null

    implicitHeight: body.implicitHeight

    Component.onCompleted: radmin.refresh_status()
    onVisibleChanged: if (visible) radmin.refresh_status()

    Connections {
        target: radmin
        function onError(message) {
            if (section.toast)
                section.toast.show_error(message)
            if (attachPanel.visible)
                attachPanel.close()
        }
        function onCreate_done(ok, message) {
            if (ok) {
                if (section.toast)
                    section.toast.show(message)
                createPanel.close()
            } else if (section.toast) {
                section.toast.show_error(message)
            }
        }
        function onAttach_done(ok, message) {
            if (ok) {
                if (section.toast)
                    section.toast.show(message)
                attachPanel.close()
            } else if (section.toast) {
                section.toast.show_error(message)
            }
        }
        function onRemove_done(ok, message) {
            if (!section.toast)
                return
            if (ok)
                section.toast.show(message)
            else
                section.toast.show_error(message)
        }
        function onVms_listed(vms) {
            attachPanel.vms = vms
        }
    }

    component ActionCard : Rectangle {
        id: card
        property string title: ""
        property string description: ""
        signal activated()

        Layout.fillWidth: true
        implicitHeight: cardBody.implicitHeight + 32
        radius: Theme.radius
        color: cardHover.hovered && !radmin.busy ? Theme.field : Theme.surface
        border.color: Theme.hairline
        opacity: radmin.busy ? 0.55 : 1
        Behavior on color { ColorAnimation { duration: 120 } }

        ColumnLayout {
            id: cardBody
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            spacing: 4
            Label {
                text: card.title
                color: Theme.text_primary
                font.pixelSize: Theme.font_body
                font.bold: true
            }
            Label {
                text: card.description
                color: Theme.text_secondary
                font.pixelSize: Theme.font_small
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        HoverHandler {
            id: cardHover
            enabled: !radmin.busy
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            enabled: !radmin.busy
            onTapped: card.activated()
        }
    }

    ColumnLayout {
        id: body
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 18

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: statusRow.implicitHeight + 24
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.hairline

            RowLayout {
                id: statusRow
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                spacing: 12

                Label {
                    text: radmin.status.ready ? "Bridge ready ✓" : "Bridge not ready ✗"
                    color: radmin.status.ready ? Theme.success : Theme.warning
                    font.pixelSize: Theme.font_body
                    font.bold: true
                }
                MilaBusyIndicator {
                    visible: radmin.busy
                    implicitWidth: 24
                    implicitHeight: 24
                }
                Item { Layout.fillWidth: true }
                MilaButton {
                    variant: "ghost"
                    text: "Check"
                    onClicked: radmin.refresh_status()
                }
            }
        }

        ActionCard {
            title: "Create bridge"
            description: "Set up the network bridge for your RadminVPN IP"
            onActivated: createPanel.open()
        }

        ActionCard {
            title: "Attach VM"
            description: "Connect adapter 2 of a VirtualBox VM to the bridge"
            onActivated: attachPanel.open()
        }

        ActionCard {
            title: "Remove bridge"
            description: "Take the bridge down until you set it up again"
            onActivated: removeDialog.open()
        }

        Label {
            Layout.fillWidth: true
            text: "1. Create a Windows VM in VirtualBox and install RadminVPN on it\n"
                  + "2. Create bridge with your RadminVPN IP\n"
                  + "3. Shut down the VM, then Attach VM\n"
                  + "4. In Windows, open ncpa.cpl and bridge the Ethernet 2 and Radmin VPN adapters\n\n"
                  + "Note: the bridge does not survive a reboot; create it again after restarting Linux."
            color: Theme.text_secondary
            font.pixelSize: Theme.font_small
            wrapMode: Text.WordWrap
        }
    }

    SidePanel {
        id: createPanel
        title: "Create bridge"
        onOpened: {
            ipField.text = backend.radmin_ip
            ipField.forceActiveFocus()
        }

        Label {
            width: parent.width
            text: "Set up the network bridge for your RadminVPN IP"
            color: Theme.text_secondary
            font.pixelSize: Theme.font_body
            wrapMode: Text.WordWrap
        }

        MilaTextField {
            id: ipField
            width: parent.width
            placeholderText: "26.x.x.x"
        }

        Label {
            width: parent.width
            text: "You may be asked for your password."
            color: Theme.text_dim
            font.pixelSize: Theme.font_small
            wrapMode: Text.WordWrap
        }

        MilaButton {
            width: parent.width
            text: "Create"
            variant: "primary"
            enabled: ipField.text.length > 0 && !radmin.busy
            onClicked: radmin.create_bridge(ipField.text)
        }

        MilaBusyIndicator {
            visible: radmin.busy
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    SidePanel {
        id: attachPanel
        title: "Attach VM"

        property var vms: null

        onOpened: {
            vms = null
            radmin.request_vms()
        }

        Label {
            width: parent.width
            text: "Pick the VM that runs RadminVPN — it must be powered off"
            color: Theme.text_secondary
            font.pixelSize: Theme.font_body
            wrapMode: Text.WordWrap
        }

        MilaBusyIndicator {
            visible: attachPanel.vms === null
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Repeater {
            model: attachPanel.vms !== null ? attachPanel.vms : []
            delegate: Rectangle {
                id: vmEntry
                required property string modelData

                width: parent ? parent.width : 0
                implicitHeight: Theme.control_height
                radius: Theme.radius_small
                color: vmHover.hovered && !radmin.busy ? Theme.hover : "transparent"
                opacity: radmin.busy ? 0.4 : 1
                Behavior on color { ColorAnimation { duration: 150 } }

                Label {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: vmEntry.modelData
                    color: Theme.text_primary
                    font.pixelSize: Theme.font_body
                    elide: Text.ElideRight
                }

                HoverHandler {
                    id: vmHover
                    enabled: !radmin.busy
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler {
                    enabled: !radmin.busy
                    onTapped: radmin.attach_vm(vmEntry.modelData)
                }
            }
        }
    }

    MilaDialog {
        id: removeDialog
        anchors.centerIn: Overlay.overlay
        modal: true
        width: 440
        title: "Remove bridge"

        Label {
            width: removeDialog.availableWidth
            text: "Removing the bridge prevents the VM from starting until you set it up again"
            color: Theme.text_soft
            font.pixelSize: Theme.font_body
            wrapMode: Text.Wrap
        }

        footer: MilaDialogButtonBox {
            MilaButton {
                text: "Continue"
                variant: "secondary"
                destructive: true
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            }
            MilaButton {
                text: "Cancel"
                variant: "ghost"
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            }
        }

        onAccepted: radmin.remove_bridge()
    }
}
