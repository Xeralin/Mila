pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../components"

Page {
    id: page
    property bool checkedOnce: false
    property string applyMessage: ""

    background: Rectangle { color: Theme.background }

    onVisibleChanged: {
        if (visible && !checkedOnce) {
            checkedOnce = true
            updater.check()
        }
    }

    Connections {
        target: updater
        function onError(message) { toast.show_error(message) }
        function onApply_progress(message) { page.applyMessage = message }
        function onBusy_changed() { page.applyMessage = "" }
        function onRestart_required() { restartDialog.open() }
    }

    ColumnLayout {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 40
        anchors.bottomMargin: 28
        width: Math.min(parent.width - 96, 600)
        spacing: 18

        Label {
            text: "Updates"
            color: Theme.text_primary
            font.pixelSize: Theme.font_title
            font.weight: Font.ExtraBold
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            visible: updater.checking
            MilaBusyIndicator { implicitWidth: 26; implicitHeight: 26; running: parent.visible }
            Label { text: "Checking for updates…"; color: Theme.text_secondary; font.pixelSize: Theme.font_body }
        }

        Label {
            visible: !updater.checking && updater.updates.length === 0 && updater.status !== "failed"
            text: "Everything is up to date"
            color: Theme.text_secondary
            font.pixelSize: Theme.font_body
        }

        Label {
            visible: !updater.checking && updater.status === "failed"
            text: "Update check failed — check your connection"
            color: Theme.warning
            font.pixelSize: Theme.font_body
        }

        Repeater {
            model: updater.checking ? [] : updater.updates
            delegate: Rectangle {
                id: entry
                required property var modelData

                Layout.fillWidth: true
                implicitHeight: 72
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.hairline

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 18
                    anchors.rightMargin: 18
                    spacing: 12

                    ColumnLayout {
                        spacing: 2
                        Label {
                            text: entry.modelData.name
                            color: Theme.text_primary
                            font.pixelSize: Theme.font_body
                            font.bold: true
                        }
                        Label {
                            text: entry.modelData.current + "   →   " + entry.modelData.target
                            color: Theme.text_secondary
                            font.pixelSize: Theme.font_small
                        }
                    }

                    Item { Layout.fillWidth: true }

                    MilaBusyIndicator {
                        implicitWidth: 28
                        implicitHeight: 28
                        running: visible
                        visible: updater.busy === entry.modelData.key
                    }
                    MilaButton {
                        text: "Update"
                        variant: "primary"
                        visible: updater.busy !== entry.modelData.key
                        enabled: updater.busy === ""
                        onClicked: updater.apply(entry.modelData.key)
                    }
                }
            }
        }

        Label {
            visible: updater.busy !== ""
            text: page.applyMessage
            color: Theme.text_secondary
            font.pixelSize: Theme.font_small
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        Item { Layout.fillHeight: true }

        MilaButton {
            Layout.alignment: Qt.AlignLeft
            variant: "ghost"
            text: "Check again"
            enabled: !updater.checking && updater.busy === ""
            onClicked: updater.check()
        }
    }

    MilaDialog {
        id: restartDialog
        anchors.centerIn: Overlay.overlay
        modal: true
        title: "Mila updated"

        Label {
            text: "Restart now?"
            color: Theme.text_soft
            font.pixelSize: Theme.font_body
        }

        footer: MilaDialogButtonBox {
            MilaButton {
                text: "Restart"
                variant: "primary"
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            }
            MilaButton {
                text: "Later"
                variant: "ghost"
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            }
        }

        onAccepted: updater.restart()
    }

    Toast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
    }
}
