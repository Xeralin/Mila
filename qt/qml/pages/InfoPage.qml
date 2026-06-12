import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Page {
    id: page

    background: Rectangle { color: Theme.background }

    Component.onCompleted: backend.refresh_info()
    onVisibleChanged: if (visible) backend.refresh_info()

    component InfoRow : RowLayout {
        Layout.fillWidth: true
        spacing: 14
    }
    component FieldName : Label {
        color: Theme.text_secondary
        font.pixelSize: Theme.font_body
        Layout.preferredWidth: 160
    }

    ColumnLayout {
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 40
        width: Math.min(parent.width - 96, 600)
        spacing: 18

        Label {
            text: "Info"
            color: Theme.text_primary
            font.pixelSize: Theme.font_title
            font.weight: Font.ExtraBold
        }

        Rectangle {
            Layout.fillWidth: true
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.hairline
            implicitHeight: grid.implicitHeight + 24

            ColumnLayout {
                id: grid
                anchors.fill: parent
                anchors.margins: 12
                spacing: 18

                InfoRow {
                    FieldName { text: "Version" }
                    Item { Layout.fillWidth: true }
                    Label { text: backend.info_data.version || ""; color: Theme.text_primary; font.pixelSize: Theme.font_body }
                }
                InfoRow {
                    FieldName { text: "Username" }
                    Item { Layout.fillWidth: true }
                    Label { text: backend.info_data.username || ""; color: Theme.text_primary; font.pixelSize: Theme.font_body }
                }
                InfoRow {
                    FieldName { text: "Steam account" }
                    Item { Layout.fillWidth: true }
                    Label { text: backend.info_data.steam_account || ""; color: Theme.text_primary; font.pixelSize: Theme.font_body }
                }
                InfoRow {
                    FieldName { text: "Downloads" }
                    Item { Layout.fillWidth: true }
                    Label { text: backend.info_data.downloads !== undefined ? backend.info_data.downloads : ""; color: Theme.text_primary; font.pixelSize: Theme.font_body }
                }
                InfoRow {
                    FieldName { text: "Disk usage" }
                    Item { Layout.fillWidth: true }
                    Label { text: backend.info_data.disk_usage || ""; color: Theme.text_primary; font.pixelSize: Theme.font_body }
                }
                InfoRow {
                    FieldName { text: "Free disk space" }
                    Item { Layout.fillWidth: true }
                    Label { text: backend.info_data.free_disk || ""; color: Theme.text_primary; font.pixelSize: Theme.font_body }
                }
            }
        }
    }
}
