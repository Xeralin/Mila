pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "pages"

Item {
    id: appRoot
    property int currentTab: 0

    Shortcut { sequences: ["Ctrl+1"]; onActivated: appRoot.currentTab = 0 }
    Shortcut { sequences: ["Ctrl+2"]; onActivated: appRoot.currentTab = 1 }
    Shortcut { sequences: ["Ctrl+3"]; onActivated: appRoot.currentTab = 2 }
    Shortcut { sequences: ["Ctrl+4"]; onActivated: appRoot.currentTab = 3 }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: header
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            color: Theme.header

            Row {
                id: tabRow
                anchors.centerIn: parent
                spacing: 0

                Repeater {
                    id: tabs
                    model: ["Download", "Settings", "Updates", "Info"]

                    delegate: Item {
                        id: tab
                        required property int index
                        required property string modelData

                        width: label.implicitWidth + 40
                        height: header.height

                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: label.bottom
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: Qt.alpha(Theme.accent, 0) }
                                GradientStop { position: 1.0; color: Theme.accent }
                            }
                            opacity: hover.hovered ? 0.3 : 0.0
                            Behavior on opacity { NumberAnimation { duration: 150 } }
                        }

                        Label {
                            id: label
                            anchors.centerIn: parent
                            text: tab.modelData
                            font.pixelSize: Theme.font_body
                            font.bold: appRoot.currentTab === tab.index
                            font.capitalization: Font.AllUppercase
                            font.letterSpacing: 1.5
                            color: appRoot.currentTab === tab.index
                                ? Theme.text_primary
                                : (hover.hovered ? Theme.text_bright : Theme.text_dim)
                            Behavior on color { ColorAnimation { duration: 150 } }
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.left: parent.left
                            anchors.right: parent.right
                            height: 4
                            color: Theme.accent
                            opacity: appRoot.currentTab === tab.index ? 1.0 : 0.0
                            Behavior on opacity { NumberAnimation { duration: 150 } }
                        }

                        HoverHandler {
                            id: hover
                            cursorShape: Qt.PointingHandCursor
                        }
                        TapHandler { onTapped: appRoot.currentTab = tab.index }
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.hairline_faint
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: appRoot.currentTab

            DownloaderPage {}
            SettingsPage {}
            UpdatesPage {}
            InfoPage {}
        }
    }
}
