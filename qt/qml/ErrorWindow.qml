import QtQuick
import QtQuick.Controls.Basic
import "components"

ApplicationWindow {
    id: window

    property string message: ""
    readonly property int content_height: contentColumn.implicitHeight + 48

    visible: true
    title: "Mila"
    color: Theme.background
    width: 440
    height: content_height
    minimumWidth: 440
    maximumWidth: 440
    minimumHeight: content_height
    maximumHeight: content_height

    Column {
        id: contentColumn
        anchors.centerIn: parent
        width: parent.width - 48
        spacing: 16

        Label {
            width: parent.width
            text: "⚠"
            color: Theme.warning
            font.pixelSize: 28
            horizontalAlignment: Text.AlignHCenter
        }

        Label {
            width: parent.width
            text: window.message
            color: Theme.text_primary
            font.pixelSize: Theme.font_body
            wrapMode: Text.Wrap
            horizontalAlignment: Text.AlignHCenter
        }

        MilaButton {
            anchors.horizontalCenter: parent.horizontalCenter
            variant: "primary"
            text: "OK"
            onClicked: Qt.quit()
        }
    }
}
